# 部署中自动数据库迁移方案

> 生产环境安全自动迁移的最佳实践

**文档版本**: 1.0  
**适用场景**: GitHub Actions / Docker / 生产部署  
**风险等级**: 中等（需严格按规范执行）

---

## 🎯 执行摘要

**答案**: ✅ **可以，但不推荐用于首次部署，适合后续更新**

**推荐策略**:
- **首次部署**: 手动执行迁移（可控、可回滚）
- **后续更新**: 自动迁移（CI/CD流水线）
- **生产环境**: 蓝绿部署 + 自动迁移

---

## ⚠️ 自动迁移的风险

### 🔴 高风险场景

| 场景 | 风险 | 后果 |
|------|------|------|
| **迁移失败** | 应用无法启动 | 服务中断 |
| **数据丢失** | 错误的迁移脚本 | 不可逆损害 |
| **长时间锁定** | 大表结构变更 | 服务不可用 |
| **回滚困难** | 无法降级 | 数据不一致 |

### 🟡 常见问题

1. **迁移脚本未测试** → 生产环境报错
2. **并发执行** → 多个实例同时迁移 → 冲突
3. **超时设置不当** → 大表迁移超时 → 部分成功
4. **无备份** → 迁移失败无法恢复

---

## ✅ 安全的自动迁移方案

### 方案A: GitHub Actions CI/CD（推荐）

#### 1. 创建工作流文件

**文件**: `.github/workflows/deploy.yml`

```yaml
name: Deploy with Auto Migration

on:
  push:
    branches: [main]
  workflow_dispatch:  # 允许手动触发

jobs:
  # ========== 阶段1: 测试 ==========
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      
      - name: Run tests
        run: pytest tests/ -v
  
  # ========== 阶段2: 备份 ==========
  backup:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Backup Database
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          echo "Creating backup..."
          pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
          echo "Backup completed"
  
  # ========== 阶段3: 迁移 ==========
  migrate:
    needs: backup
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      # ========== 关键: 自动迁移步骤 ==========
      - name: Check for pending migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          echo "Checking migration status..."
          
          # 检查是否有待执行的迁移
          pending=$(python -m alembic current 2>&1 || echo "none")
          echo "Current revision: $pending"
          
          # 检查是否有新迁移文件
          latest=$(ls -1 alembic/versions/*.py 2>/dev/null | tail -1)
          echo "Latest migration: $latest"
      
      - name: Run database migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          echo "🚀 Starting database migration..."
          
          # 设置超时（防止长时间锁定）
          export ALEMBIC_TIMEOUT=300  # 5分钟
          
          # 执行迁移（带错误处理）
          if python -m alembic upgrade head; then
            echo "✅ Migration successful"
          else
            echo "❌ Migration failed!"
            echo "Starting rollback..."
            
            # 尝试回滚
            python -m alembic downgrade -1 || echo "Rollback failed, manual intervention required"
            
            exit 1
          fi
      
      - name: Verify migrations
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          echo "Verifying migration..."
          
          # 验证新表是否存在
          python << 'EOF'
          import os
          import sys
          from sqlalchemy import create_engine, inspect
          
          engine = create_engine(os.environ['DATABASE_URL'])
          inspector = inspect(engine)
          
          required_tables = [
              'gsc_api_usage',
              'gsc_quota_status', 
              'indexing_status',
              'content_actions'
          ]
          
          existing_tables = inspector.get_table_names()
          
          missing = [t for t in required_tables if t not in existing_tables]
          if missing:
              print(f"❌ Missing tables: {missing}")
              sys.exit(1)
          else:
              print(f"✅ All required tables exist")
          EOF
  
  # ========== 阶段4: 部署 ==========
  deploy:
    needs: migrate
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        env:
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
          SERVER_HOST: ${{ secrets.SERVER_HOST }}
        run: |
          echo "Deploying application..."
          # 这里添加你的部署脚本
          # 例如: ssh deploy@$SERVER_HOST "cd /app && git pull && docker-compose up -d"
  
  # ========== 阶段5: 健康检查 ==========
  healthcheck:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - name: Health check
        env:
          APP_URL: ${{ secrets.APP_URL }}
        run: |
          echo "Waiting for app to start..."
          sleep 30
          
          # 健康检查
          for i in {1..5}; do
            if curl -f $APP_URL/health; then
              echo "✅ Health check passed"
              exit 0
            fi
            echo "Attempt $i failed, retrying..."
            sleep 10
          done
          
          echo "❌ Health check failed"
          exit 1
```

---

### 方案B: Docker Entrypoint（容器化部署）

#### 1. 创建 Entrypoint 脚本

**文件**: `scripts/docker-entrypoint.sh`

```bash
#!/bin/bash
set -e

echo "🚀 SEO Autopilot - Container Startup"

# ========== 数据库迁移 ==========
echo "📊 Checking database migrations..."

# 等待数据库就绪
echo "Waiting for database..."
python << 'EOF'
import time
import os
from sqlalchemy import create_engine

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("❌ DATABASE_URL not set")
    exit(1)

for i in range(30):  # 重试30次
    try:
        engine = create_engine(db_url)
        connection = engine.connect()
        connection.close()
        print("✅ Database is ready")
        exit(0)
    except Exception as e:
        print(f"Waiting for database... ({i+1}/30)")
        time.sleep(2)

print("❌ Database connection timeout")
exit(1)
EOF

# 执行迁移
echo "🔄 Running database migrations..."
if python -m alembic upgrade head; then
    echo "✅ Migrations completed successfully"
else
    echo "❌ Migration failed!"
    echo "⚠️  Container will not start to prevent data corruption"
    exit 1
fi

# 验证迁移
echo "🔍 Verifying database schema..."
python << 'EOF'
import os
import sys
from sqlalchemy import create_engine, inspect

engine = create_engine(os.environ['DATABASE_URL'])
inspector = inspect(engine)
tables = inspector.get_table_names()

required = ['gsc_api_usage', 'gsc_quota_status', 'indexing_status', 'content_actions']
missing = [t for t in required if t not in tables]

if missing:
    print(f"❌ Missing tables after migration: {missing}")
    sys.exit(1)
print("✅ Database schema verified")
EOF

# ========== 启动应用 ==========
echo "🎯 Starting application..."
exec "$@"
```

#### 2. 修改 Dockerfile

```dockerfile
# ... 原有内容 ...

# 添加 entrypoint 脚本
COPY scripts/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 3. Docker Compose 配置

```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/seo_autopilot
    depends_on:
      db:
        condition: service_healthy
    # entrypoint会自动执行迁移
    
  db:
    image: postgres:14-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
```

---

### 方案C: Kubernetes Job（K8s部署）

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    "helm.sh/hook": pre-install,pre-upgrade
    "helm.sh/hook-weight": "-5"
    "helm.sh/hook-delete-policy": hook-succeeded
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migration
        image: your-app-image:latest
        command: ["python", "-m", "alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: seo-autopilot
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: your-app-image:latest
        # 启动前等待迁移完成
        initContainers:
        - name: wait-for-migration
          image: busybox
          command: ['sh', '-c', 'until nc -z db 5432; do echo waiting; sleep 2; done;']
```

---

## 🛡️ 安全最佳实践

### 1. 迁移前自动备份

```bash
#!/bin/bash
# pre-migrate-backup.sh

BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"

echo "Creating backup: $BACKUP_FILE"
pg_dump $DATABASE_URL > "/backups/$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup successful"
    
    # 上传到S3（可选）
    aws s3 cp "/backups/$BACKUP_FILE" s3://your-backup-bucket/ || true
else
    echo "❌ Backup failed, aborting migration"
    exit 1
fi
```

### 2. 迁移锁定机制

防止多个实例同时执行迁移：

```python
# src/core/migration_lock.py
import redis
import time
from contextlib import contextmanager

class MigrationLock:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.lock_key = "db_migration_lock"
        self.lock_timeout = 300  # 5分钟
    
    @contextmanager
    def acquire(self):
        # 尝试获取锁
        acquired = self.redis.set(
            self.lock_key, 
            "1", 
            ex=self.lock_timeout, 
            nx=True
        )
        
        if not acquired:
            raise Exception("Migration already in progress by another instance")
        
        try:
            yield
        finally:
            self.redis.delete(self.lock_key)

# 使用
lock = MigrationLock(redis_client)
with lock.acquire():
    alembic_upgrade()
```

### 3. 超时和重试机制

```python
# 迁移配置 alembic.ini
[alembic]
# 设置连接超时
sqlalchemy.connect_args = {"connect_timeout": 30}

# 慢查询日志
script_location = alembic

# 添加钩子脚本
[post_write_hooks]
hooks = validate_migration
validate_migration.type = console_scripts
validate_migration.entrypoint = validate_migration
```

### 4. 迁移脚本验证

```python
# 在提交前验证迁移脚本
# .github/scripts/validate_migration.py

import os
import sys
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory

def validate_migration():
    """验证迁移脚本是否正确"""
    
    # 1. 检查是否有冲突的迁移头
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    
    heads = script.get_heads()
    if len(heads) > 1:
        print(f"❌ Multiple migration heads detected: {heads}")
        print("Please merge migrations before deploying")
        return False
    
    # 2. 检查是否有降级脚本
    for rev in script.walk_revisions():
        if rev.down_revision is None:
            continue  # 第一个迁移
        
        # 验证 downgrade 存在
        if not rev.module.downgrade:
            print(f"⚠️  Migration {rev.revision} missing downgrade")
    
    print("✅ Migration validation passed")
    return True

if __name__ == "__main__":
    if not validate_migration():
        sys.exit(1)
```

---

## 📋 完整的自动迁移流程

```
代码推送
   ↓
GitHub Actions触发
   ↓
阶段1: 测试
   ├─ 单元测试
   ├─ 集成测试
   └─ 迁移脚本验证
   ↓
阶段2: 备份（关键！）
   ├─ 创建数据库备份
   ├─ 上传到S3
   └─ 验证备份完整性
   ↓
阶段3: 获取迁移锁
   └─ Redis分布式锁
   ↓
阶段4: 执行迁移
   ├─ 运行alembic upgrade head
   ├─ 超时控制（5分钟）
   └─ 错误捕获和回滚
   ↓
阶段5: 验证迁移
   ├─ 检查新表是否存在
   ├─ 检查表结构
   └─ 连接测试
   ↓
阶段6: 部署应用
   ├─ 构建Docker镜像
   ├─ 推送到Registry
   └─ 更新K8s/ECS
   ↓
阶段7: 健康检查
   ├─ 等待应用启动
   ├─ 调用/health端点
   └─ 检查错误日志
   ↓
阶段8: 通知
   ├─ Slack通知
   └─ 邮件通知
```

---

## 🚨 故障处理和回滚

### 自动回滚脚本

```bash
#!/bin/bash
# rollback.sh

echo "🔄 Starting rollback..."

# 1. 停止应用
docker-compose stop app

# 2. 回滚数据库
echo "Rolling back database..."
python -m alembic downgrade -1

if [ $? -ne 0 ]; then
    echo "❌ Alembic rollback failed, trying restore from backup..."
    
    # 3. 从备份恢复
    LATEST_BACKUP=$(ls -t /backups/*.sql | head -1)
    echo "Restoring from: $LATEST_BACKUP"
    
    psql $DATABASE_URL < $LATEST_BACKUP
fi

# 4. 回滚代码
git reset --hard HEAD~1
git push origin main --force

# 5. 重启应用
docker-compose up -d

echo "✅ Rollback completed"
```

### GitHub Actions回滚工作流

```yaml
name: Rollback

on:
  workflow_dispatch:  # 手动触发

jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 获取完整历史
      
      - name: Rollback database
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          pip install -r requirements.txt
          python -m alembic downgrade -1
      
      - name: Rollback code
        run: |
          git revert HEAD --no-edit
          git push origin main
      
      - name: Notify
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
            -H 'Content-Type: application/json' \
            -d '{"text":"⚠️ Production rollback completed"}'
```

---

## ✅ 自动迁移检查清单

### 部署前必须确认

- [ ] **测试环境验证**: 迁移在测试环境已成功执行
- [ ] **备份策略**: 自动备份脚本已配置
- [ ] **回滚方案**: 可一键回滚到上一版本
- [ ] **监控告警**: 迁移失败会发送通知
- [ ] **锁定机制**: 防止并发迁移冲突
- [ ] **超时设置**: 避免长时间锁定表
- [ ] **数据验证**: 迁移后自动验证数据完整性

### 推荐的迁移触发条件

```yaml
# 只在以下情况自动执行迁移
on:
  push:
    branches: [main]
    paths:  # 只有这些文件变更时才触发
      - 'src/models/**'
      - 'alembic/versions/**'
      - 'requirements.txt'
```

---

## 🎯 总结建议

### 生产环境推荐配置

**首次部署（手动）**:
```bash
# 1. 手动执行迁移
python -m alembic upgrade head

# 2. 验证
# 3. 推送代码
```

**后续更新（自动）**:
```yaml
# GitHub Actions自动执行
- 测试通过 ✓
- 自动备份 ✓
- 自动迁移 ✓
- 健康检查 ✓
- 失败自动回滚 ✓
```

### 关键安全原则

1. **永远备份**: 迁移前自动备份数据库
2. **渐进部署**: 先测试环境，再生产环境
3. **快速回滚**: 5分钟内可回滚到上一版本
4. **监控告警**: 迁移失败立即通知
5. **锁定机制**: 防止并发执行迁移

---

**结论**: ✅ **可以实现自动迁移，但必须包含备份、验证和回滚机制。首次建议手动执行，后续使用CI/CD自动执行。**

**实施复杂度**: 中等（需要配置GitHub Actions或修改Dockerfile）

**风险等级**: 低（如果严格按照本方案执行）
