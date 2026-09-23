# -*- coding: utf-8 -*-
from yookassa.domain.common import BaseObject


class PosLinkRecipient(BaseObject):
    """
    Идентификатор торговой точки, привязанной к кассовой ссылке.
    """  # noqa: E501

    __gateway_id = None
    """Идентификатор торговой точки. Например, конкретной кассы в вашем магазине."""  # noqa: E501

    @property
    def gateway_id(self):
        """
        Возвращает gateway_id модели PosLinkRecipient.

        :return: gateway_id модели PosLinkRecipient.
        :rtype: str
        """
        return self.__gateway_id

    @gateway_id.setter
    def gateway_id(self, value):
        """
        Устанавливает gateway_id модели PosLinkRecipient.

        :param value: gateway_id модели PosLinkRecipient.
        :type value: str
        """
        self.__gateway_id = str(value)
