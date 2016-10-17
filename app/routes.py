from .views import index, update


def setup_routes(app):
    app.router.add_get('/', index, name='index')
    app.router.add_get('/update', update, name='update')
