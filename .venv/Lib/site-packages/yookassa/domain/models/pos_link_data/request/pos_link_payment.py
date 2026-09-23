# -*- coding: utf-8 -*-
from yookassa.domain.common import BaseObject


class PosLinkPayment(BaseObject):
    """
    Данные о кассовой ссылке для проведения платежа в офлайне.
    """  # noqa: E501

    __id = None
    """Идентификатор кассовой ссылки в ЮKassa."""  # noqa: E501

    __expires_at = None
    """Срок действия оплаты. Может составлять от 1 до 20 минут с момента создания платежа, по умолчанию 20 минут. Указывается по UTC и передается в формате ISO 8601."""  # noqa: E501

    @property
    def id(self):
        """
        Возвращает id модели PosLinkPayment.

        :return: id модели PosLinkPayment.
        :rtype: str
        """
        return self.__id

    @id.setter
    def id(self, value):
        """
        Устанавливает id модели PosLinkPayment.

        :param value: id модели PosLinkPayment.
        :type value: str
        """
        self.__id = value

    @property
    def expires_at(self):
        """
        Возвращает expires_at модели PosLinkPayment.

        :return: expires_at модели PosLinkPayment.
        :rtype: datetime
        """
        return self.__expires_at

    @expires_at.setter
    def expires_at(self, value):
        """
        Устанавливает expires_at модели PosLinkPayment.

        :param value: expires_at модели PosLinkPayment.
        :type value: datetime
        """
        self.__expires_at = value
