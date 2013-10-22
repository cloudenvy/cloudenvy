import pkg_resources

def _get_cloud_api(name):
    for ep in pkg_resources.iter_entry_points(group='cloudenvy_cloud_apis', name=name):
        yield ep.load()

def get_api_cls(cloud_type):
    apis = list(_get_cloud_api(cloud_type))
    return apis[0]
