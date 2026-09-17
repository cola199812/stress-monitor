from app import create_app
import os

app = create_app()

# CORS 配置已在 app/__init__.py 中统一管理

if __name__ == '__main__':
    host = os.getenv('BACKEND_HOST') or os.getenv('FLASK_RUN_HOST') or '127.0.0.1'
    port_str = os.getenv('BACKEND_PORT') or os.getenv('FLASK_RUN_PORT') or '5050'
    try:
        port = int(port_str)
    except Exception:
        port = 5050
    debug = (os.getenv('FLASK_DEBUG', '1').lower() in ('1', 'true', 'yes'))
    app.run(host=host, port=port, debug=debug)

    # # 关闭debug模式以避免过度的文件监控
    # debug = False
    
    # app.run(host=host, port=port, debug=debug, use_reloader=False)
