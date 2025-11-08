import os

class Config:
    """应用配置"""
    # 密钥
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///gallery.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # URL生成配置（用于反向代理环境）
    PREFERRED_URL_SCHEME = 'http'  # 如果使用HTTPS，改为'https'
    
    # 上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static', 'uploads')
    THUMBNAIL_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static', 'thumbnails')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = None  # 不限制总请求大小，在前端检查单个文件大小
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 单个文件最大16MB
    
    # 缩略图配置
    THUMBNAIL_SIZE = (400, 400)
    
    # 分页配置
    IMAGES_PER_PAGE = 12

    # 管理员密码（明文，启动时会自动转换为哈希）
    # 修改此密码后重启应用即可生效
    ADMIN_PASSWORD = 'admin'

    # 防盗链配置
    ENABLE_HOTLINK_PROTECTION = True  # 是否启用防盗链
    ALLOWED_DOMAINS = [
        'localhost',
        '127.0.0.1',
        # 在这里添加允许的域名，例如：
        # 'yourdomain.com',
        # 'www.yourdomain.com',
    ]
