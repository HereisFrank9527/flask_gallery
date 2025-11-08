from flask import Flask
from app.config import Config
from app.models import db
from werkzeug.security import generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_caching import Cache
import os

# 初始化缓存
cache = Cache()


def create_app(config_class=Config):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 配置ProxyFix中间件，用于在反向代理后正确处理请求
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # 将明文密码转换为哈希
    if 'ADMIN_PASSWORD' in app.config:
        app.config['ADMIN_PASSWORD_HASH'] = generate_password_hash(app.config['ADMIN_PASSWORD'])

    # 初始化缓存
    cache.init_app(app, config={
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300
    })

    # 初始化数据库
    db.init_app(app)

    # 确保上传和缩略图目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['THUMBNAIL_FOLDER'], exist_ok=True)

    # 添加 strict_slashes=False 避免重定向问题（必须在注册蓝图之前）
    app.url_map.strict_slashes = False

    # 注册蓝图
    from app.routes import main_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    # 添加上下文处理器，使网站设置在所有模板中可用
    @app.context_processor
    def inject_site_settings():
        from app.models import SiteSettings
        settings = SiteSettings.query.first()
        if not settings:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
        return dict(site_settings=settings)

    # 创建数据库表
    with app.app_context():
        db.create_all()

    return app
