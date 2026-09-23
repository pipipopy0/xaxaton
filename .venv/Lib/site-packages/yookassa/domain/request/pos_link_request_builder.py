# -*- coding: utf-8 -*-
from yookassa.domain.request.pos_link_request import CreatePosLinkRequest


class PosLinkRequestBuilder(object):
    """
    Конструктор запроса на создание кассовой ссылки.
    """  # noqa: E501

    def __init__(self):
        self.__request = CreatePosLinkRequest()

    def set_recipient(self, value):
        """
        Устанавливает recipient модели PosLinkRequestBuilder.

        :param value: recipient модели PosLinkRequestBuilder.
        :type value: PosLinkRecipient
        :rtype: PosLinkRequestBuilder
        """
        self.__request.recipient = value
        return self

    def set_pos_link_data(self, value):
        """
        Устанавливает pos_link_data модели PosLinkRequestBuilder.

        :param value: pos_link_data модели PosLinkRequestBuilder.
        :type value: PosLinkData
        :rtype: PosLinkRequestBuilder
        """
        self.__request.pos_link_data = value
        return self

    def build(self):
        """
        Возвращает request модели PosLinkRequestBuilder.

        :return: request модели PosLinkRequestBuilder.
        :rtype: CreatePosLinkRequest
        """
        return self.__request
