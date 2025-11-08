# 壁纸分享平台

一个基于Flask的个人壁纸分享网站，支持图片上传、标签管理、筛选和访客点赞功能。

## 功能特性

- **首页**: 展示最新上传的壁纸缩略图
- **画廊**: 浏览所有壁纸
- **筛选**: 根据标签筛选壁纸
- **图片详情**: 查看原图、点赞、浏览标签
- **管理后台**:
  - 密码保护的管理员登录系统
  - 批量上传图片并添加标签
  - 编辑图片信息
  - 删除图片
  - 管理标签
  - 查看统计数据
  - 修改管理员密码
- **访客点赞**: 基于IP地址的点赞系统（同一IP对同一图片只能点赞一次）
- **缩略图**: 自动生成缩略图节省流量
- **安全性**: 前台不显示管理入口，管理后台需要密码登录

## 技术栈

- **后端**: Flask 3.0
- **数据库**: SQLite (通过Flask-SQLAlchemy)
- **图片处理**: Pillow
- **前端**: HTML5, CSS3, JavaScript

## 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd flask_gallery
```

2. 创建虚拟环境（可选但推荐）
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 运行应用
```bash
python run.py
```

5. 访问应用
- 前台: http://localhost:5000
- 管理后台: http://localhost:5000/admin/login
- 默认管理员密码: `admin` (首次登录后请立即修改)

## 项目结构

```
flask_gallery/
├── app/
│   ├── __init__.py          # 应用工厂
│   ├── models.py            # 数据库模型
│   ├── routes.py            # 路由和视图
│   ├── config.py            # 配置文件
│   ├── utils.py             # 工具函数
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css    # 前台样式
│   │   │   └── admin.css    # 后台样式
│   │   ├── js/
│   │   │   └── main.js      # JavaScript
│   │   ├── uploads/         # 原图存储
│   │   └── thumbnails/      # 缩略图存储
│   └── templates/
│       ├── base.html        # 前台基础模板
│       ├── index.html       # 首页
│       ├── gallery.html     # 画廊
│       ├── filter.html      # 筛选页
│       ├── image_detail.html # 图片详情
│       └── admin/           # 管理后台模板
│           ├── base.html
│           ├── dashboard.html
│           ├── images.html
│           ├── upload.html
│           ├── edit_image.html
│           └── tags.html
├── run.py                   # 应用入口
├── requirements.txt         # 依赖列表
└── README.md               # 项目说明

```

## 数据库模型

### Image (图片)
- id: 主键
- filename: 文件名
- thumbnail: 缩略图文件名
- title: 标题
- description: 描述
- upload_date: 上传时间
- views: 浏览次数
- tags: 关联的标签（多对多）
- likes: 点赞记录（一对多）

### Tag (标签)
- id: 主键
- name: 标签名称（唯一）
- images: 关联的图片（多对多）

### Like (点赞)
- id: 主键
- image_id: 图片ID（外键）
- ip_address: 访客IP地址
- created_at: 点赞时间
- 唯一约束: (image_id, ip_address)

## 配置说明

在 `app/config.py` 中可以修改以下配置：

- `SECRET_KEY`: Flask密钥
- `SQLALCHEMY_DATABASE_URI`: 数据库连接
- `UPLOAD_FOLDER`: 原图存储路径
- `THUMBNAIL_FOLDER`: 缩略图存储路径
- `ALLOWED_EXTENSIONS`: 允许的文件格式
- `MAX_CONTENT_LENGTH`: 最大上传文件大小
- `THUMBNAIL_SIZE`: 缩略图尺寸
- `IMAGES_PER_PAGE`: 每页显示图片数量
- `ADMIN_PASSWORD`: 管理员密码（明文，启动时自动转换为哈希）
- `ENABLE_HOTLINK_PROTECTION`: 是否启用防盗链（True/False）
- `ALLOWED_DOMAINS`: 允许访问图片的域名列表

## 使用说明

### 修改管理员密码（直接编辑配置文件）
1. 打开 `app/config.py` 文件
2. 找到 `ADMIN_PASSWORD = 'admin'` 这一行
3. 将 `'admin'` 改为你的新密码
4. 保存文件并重启应用
5. 使用新密码登录管理后台

### 配置防盗链
1. 打开 `app/config.py` 文件
2. 设置 `ENABLE_HOTLINK_PROTECTION = True` 启用防盗链
3. 在 `ALLOWED_DOMAINS` 列表中添加允许的域名：
```python
ALLOWED_DOMAINS = [
    'localhost',
    '127.0.0.1',
    'yourdomain.com',
    'www.yourdomain.com',
]
```
4. 保存文件并重启应用

### 管理员登录
1. 访问管理后台登录页 `/admin/login`
2. 输入密码（默认: `admin`）
3. 首次登录后建议立即修改密码

### 在管理后台修改密码
1. 登录管理后台
2. 点击"修改密码"
3. 输入旧密码和新密码
4. 新密码会自动保存到 `config.py` 文件

### 批量上传图片
1. 登录管理后台
2. 点击"上传图片"
3. 选择多张图片文件（可按住Ctrl或Shift多选）
4. 填写描述和标签（应用于所有图片）
5. 点击批量上传

### 筛选图片
1. 访问筛选页面 `/filter`
2. 勾选想要的标签
3. 点击"应用筛选"

### 点赞图片
1. 进入图片详情页
2. 点击"点赞"按钮
3. 再次点击可取消点赞

## 注意事项

- 首次运行会自动创建数据库和必要的目录
- 默认管理员密码为 `admin`，可直接在 `config.py` 中修改
- 管理员密码以明文形式存储在配置文件中，启动时自动转换为哈希
- 前台不显示管理后台入口，需直接访问 `/admin/login`
- 上传的图片会自动生成缩略图
- 批量上传时，所有图片共享相同的描述和标签
- 批量上传的图片不会自动设置标题
- 同一IP对同一图片只能点赞一次
- 删除图片会同时删除原图、缩略图和数据库记录
- 防盗链功能默认启用，只允许配置的域名访问图片
- 图片通过专用路由访问，不直接暴露static文件夹路径

## 许可证

MIT License
