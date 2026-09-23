# -*- coding: utf-8 -*-
from yookassa.domain.common.response_object import ResponseObject
from yookassa.domain.models.pos_link_data.response.pos_link_last_payment import PosLinkLastPayment
from yookassa.domain.models.pos_link_data.pos_link_recipient import PosLinkRecipient


class PosLinkResponse(ResponseObject):
    """
    Объект кассовой ссылки — актуальная информация о кассовой ссылке.
    """  # noqa: E501

    __id = None
    """Идентификатор кассовой ссылки в ЮKassa."""  # noqa: E501

    __status = None
    """Статус кассовой ссылки. Возможные значения: `active`, `inactive`."""  # noqa: E501

    __type = None
    """Тип кассовой ссылки — провайдер, доступный для проведения платежей по этой кассовой ссылке. Возможные значения: `nspk`."""  # noqa: E501

    __recipient = None
    """Идентификатор торговой точки, которая привязана к кассовой ссылке."""  # noqa: E501

    __payment = None
    """Данные о последнем платеже, который прошел по этой кассовой ссылке."""  # noqa: E501

    @property
    def id(self):
        """
        Возвращает id модели PosLinkResponse.

        :return: id модели PosLinkResponse.
        :rtype: str
        """
        return self.__id

    @id.setter
    def id(self, value):
        """
        Устанавливает id модели PosLinkResponse.

        :param value: id модели PosLinkResponse.
        :type value: str
        """
        self.__id = value

    @property
    def status(self):
        """
        Возвращает status модели PosLinkResponse.

        :return: status модели PosLinkResponse.
        :rtype: str
        """
        return self.__status

    @status.setter
    def status(self, value):
        """
        Устанавливает status модели PosLinkResponse.

        :param value: status модели PosLinkResponse.
        :type value: str
        """
        self.__status = value

    @property
    def type(self):
        """
        Возвращает type модели PosLinkResponse.

        :return: type модели PosLinkResponse.
        :rtype: str
        """
        return self.__type

    @type.setter
    def type(self, value):
        """
        Устанавливает type модели PosLinkResponse.

        :param value: type модели PosLinkResponse.
        :type value: str
        """
        self.__type = value

    @property
    def recipient(self):
        """
        Возвращает recipient модели PosLinkResponse.

        :return: recipient модели PosLinkResponse.
        :rtype: PosLinkRecipient
        """
        return self.__recipient

    @recipient.setter
    def recipient(self, value):
        """
        Устанавливает recipient модели PosLinkResponse.

        :param value: recipient модели PosLinkResponse.
        :type value: PosLinkRecipient
        """
        if isinstance(value, dict):
            self.__recipient = PosLinkRecipient(value)
        elif isinstance(value, PosLinkRecipient):
            self.__recipient = value
        else:
            self.__recipient = value

    @property
    def payment(self):
        """
        Возвращает payment модели PosLinkResponse.

        :return: payment модели PosLinkResponse.
        :rtype: PosLinkLastPayment
        """
        return self.__payment

    @payment.setter
    def payment(self, value):
        """
        Устанавливает payment модели PosLinkResponse.

        :param value: payment модели PosLinkResponse.
        :type value: PosLinkLastPayment
        """
        if isinstance(value, dict):
            self.__payment = PosLinkLastPayment(value)
        elif isinstance(value, PosLinkLastPayment):
            self.__payment = value
        else:
            self.__payment = value
