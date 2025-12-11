#!/usr/bin/env python3
"""
Test script to validate config hash generation consistency.

This script ensures that:
1. Same configuration always generates the same hash
2. Different configurations generate different hashes
3. Hash generation is deterministic across multiple runs
"""

import hashlib
import yaml
from datetime import datetime


def generate_config_hash(config_dict: dict) -> str:
    """
    Generate a deterministic hash from circuit configuration.
    
    This matches the implementation in scripts/generate_circuit_configs.py
    """
    # Remove metadata field to avoid circular dependency
    config_copy = config_dict.copy()
    config_copy.pop('metadata', None)
    
    # Convert to YAML string with sorted keys for deterministic output
    yaml_str = yaml.dump(config_copy, sort_keys=True, default_flow_style=False)
    
    # Generate MD5 hash and truncate to 12 characters
    hash_md5 = hashlib.md5(yaml_str.encode('utf-8'))
    return hash_md5.hexdigest()[:12]


def test_hash_consistency():
    """Test that same config always produces same hash."""
    print("Test 1: Hash Consistency")
    print("-" * 60)
    
    config = {
        'plant_id': 'PLANT001',
        'circuit_id': 'CIRCUIT01',
        'cutoff_date': '2025-12-11',
        'model_name': 'plant001-circuit01',
        'hyperparameters': {
            'learning_rate': 0.001,
            'epochs': 100,
            'batch_size': 32
        }
    }
    
    # Generate hash 5 times
    hashes = [generate_config_hash(config) for _ in range(5)]
    
    # All should be identical
    if len(set(hashes)) == 1:
        print(f"✅ PASS: All hashes identical: {hashes[0]}")
    else:
        print(f"❌ FAIL: Inconsistent hashes: {hashes}")
        return False
    
    print()
    return True


def test_hash_uniqueness():
    """Test that different configs produce different hashes."""
    print("Test 2: Hash Uniqueness")
    print("-" * 60)
    
    config1 = {
        'plant_id': 'PLANT001',
        'circuit_id': 'CIRCUIT01',
        'cutoff_date': '2025-12-11',
        'hyperparameters': {'learning_rate': 0.001}
    }
    
    config2 = {
        'plant_id': 'PLANT001',
        'circuit_id': 'CIRCUIT01',
        'cutoff_date': '2025-12-18',  # Different cutoff_date
        'hyperparameters': {'learning_rate': 0.001}
    }
    
    config3 = {
        'plant_id': 'PLANT001',
        'circuit_id': 'CIRCUIT01',
        'cutoff_date': '2025-12-11',
        'hyperparameters': {'learning_rate': 0.01}  # Different learning_rate
    }
    
    hash1 = generate_config_hash(config1)
    hash2 = generate_config_hash(config2)
    hash3 = generate_config_hash(config3)
    
    print(f"Config 1 hash: {hash1}")
    print(f"Config 2 hash: {hash2} (different cutoff_date)")
    print(f"Config 3 hash: {hash3} (different learning_rate)")
    
    if hash1 != hash2 and hash1 != hash3 and hash2 != hash3:
        print("✅ PASS: All hashes are unique")
    else:
        print("❌ FAIL: Hash collision detected")
        return False
    
    print()
    return True


def test_metadata_exclusion():
    """Test that metadata field doesn't affect hash."""
    print("Test 3: Metadata Exclusion")
    print("-" * 60)
    
    config_without_metadata = {
        'plant_id': 'PLANT001',
        'circuit_id': 'CIRCUIT01',
        'cutoff_date': '2025-12-11',
        'hyperparameters': {'learning_rate': 0.001}
    }
    
    config_with_metadata = {
        'plant_id': 'PLANT001',
        'circuit_id': 'CIRCUIT01',
        'cutoff_date': '2025-12-11',
        'hyperparameters': {'learning_rate': 0.001},
        'metadata': {
            'config_hash': 'some_hash',
            'generated_at': '2025-12-11T10:00:00Z',
            'description': 'This should be ignored'
        }
    }
    
    hash1 = generate_config_hash(config_without_metadata)
    hash2 = generate_config_hash(config_with_metadata)
    
    print(f"Hash without metadata: {hash1}")
    print(f"Hash with metadata:    {hash2}")
    
    if hash1 == hash2:
        print("✅ PASS: Metadata correctly excluded from hash")
    else:
        print("❌ FAIL: Metadata affecting hash")
        return False
    
    print()
    return True


def test_dict_ordering():
    """Test that dict key ordering doesn't affect hash."""
    print("Test 4: Dictionary Key Ordering")
    print("-" * 60)
    
    # Same config but different key order
    config1 = {
        'plant_id': 'PLANT001',
        'circuit_id': 'CIRCUIT01',
        'cutoff_date': '2025-12-11',
        'hyperparameters': {'learning_rate': 0.001, 'epochs': 100}
    }
    
    config2 = {
        'cutoff_date': '2025-12-11',
        'hyperparameters': {'epochs': 100, 'learning_rate': 0.001},
        'circuit_id': 'CIRCUIT01',
        'plant_id': 'PLANT001'
    }
    
    hash1 = generate_config_hash(config1)
    hash2 = generate_config_hash(config2)
    
    print(f"Hash (order 1): {hash1}")
    print(f"Hash (order 2): {hash2}")
    
    if hash1 == hash2:
        print("✅ PASS: Key ordering doesn't affect hash (deterministic)")
    else:
        print("❌ FAIL: Key ordering affects hash (non-deterministic)")
        return False
    
    print()
    return True


def test_collision_probability():
    """Calculate theoretical collision probability."""
    print("Test 5: Collision Probability Analysis")
    print("-" * 60)
    
    # 12 hex characters = 12 * 4 bits = 48 bits
    # Total possible values = 16^12 = 2^48
    total_values = 16 ** 12
    
    # For 100 circuits, probability of collision (birthday paradox)
    # P(collision) ≈ n^2 / (2 * total_values)
    n = 100  # Number of circuits
    collision_prob = (n ** 2) / (2 * total_values)
    
    print(f"Hash space: {total_values:,} possible values")
    print(f"Number of circuits: {n}")
    print(f"Collision probability: {collision_prob:.2e} ({collision_prob * 100:.10f}%)")
    print(f"Collision probability: ~1 in {1/collision_prob:,.0f}")
    
    if collision_prob < 1e-9:  # Less than 1 in a billion
        print("✅ PASS: Collision probability acceptably low")
    else:
        print("⚠️  WARNING: Consider using longer hash")
        return False
    
    print()
    return True


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("Config Hash Validation Tests")
    print("=" * 60 + "\n")
    
    tests = [
        test_hash_consistency,
        test_hash_uniqueness,
        test_metadata_exclusion,
        test_dict_ordering,
        test_collision_probability
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ FAIL: {test.__name__} raised exception: {e}\n")
            results.append(False)
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    exit(main())
