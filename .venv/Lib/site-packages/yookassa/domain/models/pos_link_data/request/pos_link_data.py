# -*- coding: utf-8 -*-
from yookassa.domain.common import BaseObject


class PosLinkData(BaseObject):
    """
    Данные кассовой ссылки.
    """  # noqa: E501

    __link = None
    """Кассовая ссылка с платежной таблички. Чтобы получить ее, отсканируйте QR-код на табличке."""  # noqa: E501

    @property
    def link(self):
        """
        Возвращает link модели PosLinkData.

        :return: link модели PosLinkData.
        :rtype: str
        """
        return self.__link

    @link.setter
    def link(self, value):
        """
        Устанавливает link модели PosLinkData.

        :param value: link модели PosLinkData.
        :type value: str
        """
        cast_value = str(value)
        if cast_value:
            self.__link = cast_value
