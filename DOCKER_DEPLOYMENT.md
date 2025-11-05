# Whatalert 监控告警系统 - Docker & Kubernetes 部署指南

## 📦 Docker 部署

### 1. 使用 Docker Compose（推荐用于测试/开发）

#### 快速启动

```bash
# 克隆代码
git clone <your-repo>
cd Whatalert

# 配置环境
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml，配置数据库和Redis连接

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### docker-compose.yml 说明

当前配置包含：
- **backend**: 后端 API 服务（端口 8000）
- **frontend**: 前端 Vue 应用（端口 80）
- **mysql**: MySQL 数据库（端口 3306）
- **redis**: Redis 缓存（端口 6379）

### 2. 单独构建镜像

#### 构建后端镜像

```bash
cd Whatalert
docker build -t whatalert-backend:latest .
```

#### 构建前端镜像

```bash
cd Whatalert/web
docker build -t whatalert-frontend:latest .
```

#### 运行容器

```bash
# 运行后端
docker run -d \
  --name whatalert-backend \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  whatalert-backend:latest

# 运行前端
docker run -d \
  --name whatalert-frontend \
  -p 80:80 \
  whatalert-frontend:latest
```

---

## ☸️  Kubernetes 部署

### 1. 准备工作

#### 创建命名空间

```bash
kubectl create namespace whatalert
```

#### 创建ConfigMap（配置文件）

```bash
kubectl create configmap whatalert-config \
  --from-file=config.yaml=config/config.yaml \
  -n whatalert
```

#### 创建Secret（敏感信息）

```bash
kubectl create secret generic whatalert-secret \
  --from-literal=mysql-root-password='your-root-password' \
  --from-literal=mysql-password='your-password' \
  --from-literal=redis-password='your-redis-password' \
  --from-literal=jwt-secret='your-jwt-secret' \
  -n whatalert
```

### 2. 部署 MySQL（使用 StatefulSet）

创建 `k8s/mysql-statefulset.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: whatalert
spec:
  ports:
  - port: 3306
    name: mysql
  clusterIP: None
  selector:
    app: mysql
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: whatalert
spec:
  serviceName: mysql
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - containerPort: 3306
          name: mysql
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: whatalert-secret
              key: mysql-root-password
        - name: MYSQL_DATABASE
          value: "whatalert"
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
        - name: init-sql
          mountPath: /docker-entrypoint-initdb.d
      volumes:
      - name: init-sql
        configMap:
          name: mysql-init-sql
  volumeClaimTemplates:
  - metadata:
      name: mysql-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

#### 创建初始化SQL的ConfigMap

```bash
kubectl create configmap mysql-init-sql \
  --from-file=init.sql=scripts/init_database.sql \
  -n whatalert
```

#### 部署MySQL

```bash
kubectl apply -f k8s/mysql-statefulset.yaml
```

### 3. 部署 Redis

创建 `k8s/redis-deployment.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: whatalert
spec:
  ports:
  - port: 6379
    name: redis
  selector:
    app: redis
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: whatalert
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command:
        - redis-server
        - --requirepass
        - $(REDIS_PASSWORD)
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: whatalert-secret
              key: redis-password
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        emptyDir: {}
```

```bash
kubectl apply -f k8s/redis-deployment.yaml
```

### 4. 部署后端服务

创建 `k8s/backend-deployment.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: whatalert-backend
  namespace: whatalert
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  selector:
    app: whatalert-backend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whatalert-backend
  namespace: whatalert
spec:
  replicas: 3  # 支持多实例（通过Redis分布式锁）
  selector:
    matchLabels:
      app: whatalert-backend
  template:
    metadata:
      labels:
        app: whatalert-backend
    spec:
      containers:
      - name: backend
        image: whatalert-backend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_HOST
          value: "mysql"
        - name: DATABASE_PORT
          value: "3306"
        - name: DATABASE_NAME
          value: "whatalert"
        - name: DATABASE_USERNAME
          value: "root"
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: whatalert-secret
              key: mysql-root-password
        - name: REDIS_HOST
          value: "redis"
        - name: REDIS_PORT
          value: "6379"
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: whatalert-secret
              key: redis-password
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: whatalert-secret
              key: jwt-secret
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: logs
          mountPath: /app/logs
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: config
        configMap:
          name: whatalert-config
      - name: logs
        emptyDir: {}
```

```bash
kubectl apply -f k8s/backend-deployment.yaml
```

### 5. 部署前端服务

创建 `k8s/frontend-deployment.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: whatalert-frontend
  namespace: whatalert
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
    name: http
  selector:
    app: whatalert-frontend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: whatalert-frontend
  namespace: whatalert
spec:
  replicas: 2
  selector:
    matchLabels:
      app: whatalert-frontend
  template:
    metadata:
      labels:
        app: whatalert-frontend
    spec:
      containers:
      - name: frontend
        image: whatalert-frontend:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
```

```bash
kubectl apply -f k8s/frontend-deployment.yaml
```

### 6. 配置 Ingress（对外暴露）

创建 `k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whatalert-ingress
  namespace: whatalert
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - whatalert.yourdomain.com
    secretName: whatalert-tls
  rules:
  - host: whatalert.yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: whatalert-backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: whatalert-frontend
            port:
              number: 80
```

```bash
kubectl apply -f k8s/ingress.yaml
```

### 7. 配置 HPA（水平自动扩缩容）

创建 `k8s/hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: whatalert-backend-hpa
  namespace: whatalert
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: whatalert-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

```bash
kubectl apply -f k8s/hpa.yaml
```

---

## 📊 监控和日志

### 查看Pod状态

```bash
kubectl get pods -n whatalert
kubectl describe pod <pod-name> -n whatalert
```

### 查看日志

```bash
# 查看后端日志
kubectl logs -f deployment/whatalert-backend -n whatalert

# 查看前端日志
kubectl logs -f deployment/whatalert-frontend -n whatalert

# 查看MySQL日志
kubectl logs -f statefulset/mysql -n whatalert

# 查看Redis日志
kubectl logs -f deployment/redis -n whatalert
```

### 进入容器

```bash
kubectl exec -it deployment/whatalert-backend -n whatalert -- /bin/bash
```

---

## 🔧 运维操作

### 扩缩容

```bash
# 手动扩容后端
kubectl scale deployment whatalert-backend --replicas=5 -n whatalert

# 手动扩容前端
kubectl scale deployment whatalert-frontend --replicas=3 -n whatalert
```

### 滚动更新

```bash
# 更新后端镜像
kubectl set image deployment/whatalert-backend \
  backend=whatalert-backend:v1.1.0 \
  -n whatalert

# 查看滚动更新状态
kubectl rollout status deployment/whatalert-backend -n whatalert

# 回滚
kubectl rollout undo deployment/whatalert-backend -n whatalert
```

### 备份数据库

```bash
# 创建备份任务
kubectl exec -it statefulset/mysql -n whatalert -- \
  mysqldump -uroot -p<password> whatalert > backup.sql
```

### 重置管理员密码

```bash
# 直接连接数据库修改（密码：admin123）
kubectl exec -it statefulset/mysql -n whatalert -- mysql -uroot -p -e \
  "UPDATE whatalert.user SET password_hash='$2b$12$cpLHuqRo2MqsW/CNjTLKPOJkG8ofG6mD3fUCMaOMA05zf3ap8rnUy' WHERE username='admin';"
```

---

## 🔐 安全建议

1. **使用Secret管理敏感信息**
   - 不要在ConfigMap中存储密码
   - 使用Kubernetes Secret或外部密钥管理工具（如Vault）

2. **启用网络策略**
   - 限制Pod间通信
   - 只允许必要的端口和协议

3. **配置资源限制**
   - 设置CPU和内存的requests和limits
   - 防止资源耗尽

4. **定期备份**
   - 备份MySQL数据
   - 备份配置文件

5. **监控告警**
   - 集成Prometheus监控
   - 配置关键指标告警

---

## 📝 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_HOST | MySQL主机 | localhost |
| DATABASE_PORT | MySQL端口 | 3306 |
| DATABASE_NAME | 数据库名 | whatalert |
| DATABASE_USERNAME | 数据库用户名 | root |
| DATABASE_PASSWORD | 数据库密码 | - |
| REDIS_HOST | Redis主机 | localhost |
| REDIS_PORT | Redis端口 | 6379 |
| REDIS_PASSWORD | Redis密码 | - |
| REDIS_DB | Redis数据库 | 0 |
| JWT_SECRET_KEY | JWT密钥 | - |
| LOG_LEVEL | 日志级别 | INFO |

---

## 🚀 完整部署命令

```bash
# 1. 创建命名空间
kubectl create namespace whatalert

# 2. 创建Secret
kubectl create secret generic whatalert-secret \
  --from-literal=mysql-root-password='YourPassword' \
  --from-literal=mysql-password='YourPassword' \
  --from-literal=redis-password='YourRedisPassword' \
  --from-literal=jwt-secret='YourJWTSecret' \
  -n whatalert

# 3. 创建ConfigMap
kubectl create configmap whatalert-config \
  --from-file=config.yaml=config/config.yaml \
  -n whatalert

kubectl create configmap mysql-init-sql \
  --from-file=init.sql=scripts/init_database.sql \
  -n whatalert

# 4. 部署所有服务
kubectl apply -f k8s/mysql-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# 5. 等待所有Pod就绪
kubectl wait --for=condition=ready pod -l app=whatalert-backend -n whatalert --timeout=300s

# 6. 访问系统
echo "访问地址: https://whatalert.yourdomain.com"
echo "默认账号: admin"
echo "默认密码: admin123"
```

---

## 📞 故障排查

### Pod 启动失败

```bash
kubectl get events -n whatalert
kubectl describe pod <pod-name> -n whatalert
kubectl logs <pod-name> -n whatalert
```

### 数据库连接失败

```bash
# 检查MySQL是否就绪
kubectl get pods -n whatalert | grep mysql

# 测试数据库连接
kubectl run -it --rm mysql-client --image=mysql:8.0 --restart=Never -n whatalert -- \
  mysql -h mysql -uroot -p
```

### Redis连接失败

```bash
# 检查Redis是否就绪
kubectl get pods -n whatalert | grep redis

# 测试Redis连接
kubectl run -it --rm redis-client --image=redis:7-alpine --restart=Never -n whatalert -- \
  redis-cli -h redis -a <password> ping
```

---

## 📚 参考资料

- [Docker 官方文档](https://docs.docker.com/)
- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [Helm Charts](https://helm.sh/)

