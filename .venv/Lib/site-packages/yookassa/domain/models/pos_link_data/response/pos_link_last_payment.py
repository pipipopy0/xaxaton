# -*- coding: utf-8 -*-
from yookassa.domain.common import BaseObject


class PosLinkLastPayment(BaseObject):
    """
    Данные о последнем платеже, который прошел по кассовой ссылке.
    """  # noqa: E501

    __id = None
    """Идентификатор платежа в ЮKassa."""  # noqa: E501

    __status = None
    """Статус платежа. Возможные значения: `pending`, `succeeded` и `canceled`."""  # noqa: E501

    @property
    def id(self):
        """
        Возвращает id модели PosLinkLastPayment.

        :return: id модели PosLinkLastPayment.
        :rtype: str
        """
        return self.__id

    @id.setter
    def id(self, value):
        """
        Устанавливает id модели PosLinkLastPayment.

        :param value: id модели PosLinkLastPayment.
        :type value: str
        """
        self.__id = value

    @property
    def status(self):
        """
        Возвращает status модели PosLinkLastPayment.

        :return: status модели PosLinkLastPayment.
        :rtype: str
        """
        return self.__status

    @status.setter
    def status(self, value):
        """
        Устанавливает status модели PosLinkLastPayment.

        :param value: status модели PosLinkLastPayment.
        :type value: str
        """
        self.__status = value
