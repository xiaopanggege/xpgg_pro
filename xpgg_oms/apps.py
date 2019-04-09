from django.apps import AppConfig


class XpggOmsConfig(AppConfig):
    name = 'xpgg_oms'

    def ready(self):
        # 加载自定义py文件
        import xpgg_oms.signals
