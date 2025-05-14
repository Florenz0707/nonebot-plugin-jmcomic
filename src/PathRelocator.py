import yaml
from pathlib import Path


class PathRelocator:
    _base_dir: Path = Path(r"")
    _config_dir: Path = _base_dir.joinpath("config")
    _default: Path = _config_dir.joinpath("default_options.yml")
    _firstImage: Path = _config_dir.joinpath("firstImage_options.yml")
    _proxy: Path = _config_dir.joinpath("proxyClient.yml")
    _login_username: str = ""
    _login_pwd: str = ""
    _proxy_host: str = ""
    _cookies_AVS: str = ""

    @classmethod
    def getBaseDir(cls):
        return cls._base_dir

    @classmethod
    def read(cls, file: Path) -> dict:
        with open(file, 'r', encoding="utf-8") as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)

    @classmethod
    def write(cls, file: Path, data: dict):
        with open(file, 'w', encoding="utf-8") as f:
            yaml.dump(data=data, stream=f, allow_unicode=True)

    @classmethod
    def load(cls):
        default = cls.read(cls._default)
        default['dir_rule']['base_dir'] = str(cls._base_dir.joinpath(r"data/album_cache"))
        default['plugins']['after_init'][1]['kwargs']['username'] = cls._login_username
        default['plugins']['after_init'][1]['kwargs']['password'] = cls._login_pwd
        default['plugins']['after_photo'][0]['kwargs']['pdf_dir'] = str(cls._base_dir.joinpath(r"data/save_cache/pdf"))
        cls.write(cls._default, default)

        first_image = cls.read(cls._firstImage)
        first_image['dir_rule']['base_dir'] = str(cls._base_dir.joinpath(r"data/album_cache"))
        first_image['plugins']['after_init'][1]['kwargs']['username'] = cls._login_username
        first_image['plugins']['after_init'][1]['kwargs']['password'] = cls._login_pwd
        cls.write(cls._firstImage, first_image)

        proxy = cls.read(cls._proxy)
        proxy['client']['postman']['meta_data']['proxies'] = cls._proxy_host
        proxy['client']['postman']['meta_data']['cookies']['AVS'] = cls._cookies_AVS
        cls.write(cls._proxy, proxy)


if __name__ == "__main__":
    PathRelocator.load()
