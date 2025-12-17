# Git Branching Strategy

Branch workflow and release process.

## Branch Structure

```
main (production)
├── release/v1.0.0 (test environment)
│   └── develop (development)
│       └── feature/* (feature branches)
```

## Branches

| Branch | Environment | Purpose | Protected |
|--------|-------------|---------|-----------|
| `main` | Production | Prod deployments | Yes (2 approvers) |
| `release/*` | Test | Test deployments | Yes (1 approver) |
| `develop` | Dev | Active development, training | No |
| `feature/*` | Local | Feature development | No |

## Workflow

### 1. Feature Development

```bash
# Create feature branch from develop
git checkout develop
git pull
git checkout -b feature/add-new-circuit

# Make changes
git add .
git commit -m "Add PLANT003/CIRCUIT01 configuration"

# Push and create PR to develop
git push origin feature/add-new-circuit
```

### 2. Development (develop branch)

**Triggers:**
- Training pipeline on push
- PR validation on PR creation

**Process:**
1. Merge feature PR to develop
2. Training pipeline runs automatically
3. Models registered in Dev workspace
4. Models promoted to Registry (with approval)

### 3. Release (release/* branches)

**Create Release:**
```bash
# From develop
git checkout -b release/v1.1.0
git push origin release/v1.1.0
```

**Triggers:**
- Test deployment pipeline

**Process:**
1. Deploy models from Registry to Test
2. QA validation
3. Bug fixes merged to release branch
4. When stable, merge to main

### 4. Production (main branch)

**Merge Release:**
```bash
# After QA approval
git checkout main
git merge release/v1.1.0
git push origin main
```

**Triggers:**
- Prod deployment pipeline (manual)

**Process:**
1. Manual trigger required
2. Deploy models from Registry to Prod
3. Blue-green deployment
4. Traffic ramp: 0% → 100%

## Release Process

### 1. Prepare Release

- [ ] All features merged to develop
- [ ] Training pipeline successful
- [ ] Models promoted to Registry
- [ ] Create release branch

### 2. Test Deployment

- [ ] Deploy to Test environment
- [ ] QA validation complete
- [ ] Performance benchmarks met
- [ ] Bug fixes applied

### 3. Production Deployment

- [ ] Merge to main
- [ ] Trigger Prod deployment
- [ ] Monitor deployment
- [ ] Verify metrics

### 4. Post-Release

- [ ] Tag release: `git tag v1.1.0`
- [ ] Update documentation
- [ ] Merge main back to develop

## Hotfix Process

**For production issues:**

```bash
# Create hotfix from main
git checkout main
git checkout -b hotfix/fix-critical-bug

# Fix and test
git commit -m "Fix critical bug"

# Merge to main and develop
git checkout main
git merge hotfix/fix-critical-bug
git checkout develop
git merge hotfix/fix-critical-bug
```

## Best Practices

1. **Never commit to main directly**
2. **Always use PRs for develop**
3. **Require PR validation to pass**
4. **Test in Test before Prod**
5. **Tag all releases**
6. **Keep develop up to date with main**
7. **Delete feature branches after merge**
