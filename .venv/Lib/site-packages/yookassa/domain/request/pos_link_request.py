# -*- coding: utf-8 -*-
from yookassa.domain.common.request_object import RequestObject
from yookassa.domain.models.pos_link_data.request.pos_link_data import PosLinkData
from yookassa.domain.models.pos_link_data.pos_link_recipient import PosLinkRecipient


class CreatePosLinkRequest(RequestObject):
    """
    Объект запроса к API на создание и активацию кассовой ссылки.
    """  # noqa: E501

    __recipient = None
    """Идентификатор торговой точки. Например, конкретной кассы в вашем магазине."""  # noqa: E501

    __pos_link_data = None
    """Данные кассовой ссылки — уникальной ссылки, зашифрованной в QR-коде и NFC-метке на платежной табличке."""  # noqa: E501

    @property
    def recipient(self):
        """
        Возвращает recipient модели CreatePosLinkRequest.

        :return: recipient модели CreatePosLinkRequest.
        :rtype: PosLinkRecipient
        """
        return self.__recipient

    @recipient.setter
    def recipient(self, value):
        """
        Устанавливает recipient модели CreatePosLinkRequest.

        :param value: recipient модели CreatePosLinkRequest.
        :type value: PosLinkRecipient
        """
        if value is None:  # noqa: E501
            raise ValueError("Invalid value for `recipient`, must not be `None`")  # noqa: E501
        if isinstance(value, dict):
            self.__recipient = PosLinkRecipient(value)
        elif isinstance(value, PosLinkRecipient):
            self.__recipient = value
        else:
            raise TypeError('Invalid recipient value type')

    @property
    def pos_link_data(self):
        """
        Возвращает pos_link_data модели CreatePosLinkRequest.

        :return: pos_link_data модели CreatePosLinkRequest.
        :rtype: PosLinkData
        """
        return self.__pos_link_data

    @pos_link_data.setter
    def pos_link_data(self, value):
        """
        Устанавливает pos_link_data модели CreatePosLinkRequest.

        :param value: pos_link_data модели CreatePosLinkRequest.
        :type value: PosLinkData
        """
        if value is None:  # noqa: E501
            raise ValueError("Invalid value for `pos_link_data`, must not be `None`")  # noqa: E501
        if isinstance(value, dict):
            self.__pos_link_data = PosLinkData(value)
        elif isinstance(value, PosLinkData):
            self.__pos_link_data = value
        else:
            raise TypeError('Invalid pos_link_data value type')


class RecipientPosLinkRequest(RequestObject):
    """
    Объект запроса к API на изменение торговой точки, привязанной к кассовой ссылке.
    """  # noqa: E501

    __recipient = None
    """Идентификатор торговой точки, которую вы хотите привязать к кассовой ссылке."""  # noqa: E501

    @property
    def recipient(self):
        """
        Возвращает recipient модели RecipientPosLinkRequest.

        :return: recipient модели RecipientPosLinkRequest.
        :rtype: PosLinkRecipient
        """
        return self.__recipient

    @recipient.setter
    def recipient(self, value):
        """
        Устанавливает recipient модели RecipientPosLinkRequest.

        :param value: recipient модели RecipientPosLinkRequest.
        :type value: PosLinkRecipient
        """
        if value is None:  # noqa: E501
            raise ValueError("Invalid value for `recipient`, must not be `None`")  # noqa: E501
        if isinstance(value, dict):
            self.__recipient = PosLinkRecipient(value)
        elif isinstance(value, PosLinkRecipient):
            self.__recipient = value
        else:
            raise TypeError('Invalid recipient value type')
