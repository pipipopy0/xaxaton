# -*- coding: utf-8 -*-
from yookassa.domain.common import ConfirmationType
from yookassa.domain.models.payment_method import SavePaymentMethodConfirmation


class SavePaymentMethodConfirmationQr(SavePaymentMethodConfirmation):
    """
    Выбранный сценарий подтверждения привязки. Присутствует, когда привязка ожидает подтверждения от пользователя.
    """  # noqa: E501

    __confirmation_data = None
    """Данные для генерации QR-кода."""   # noqa: E501

    def __init__(self, *args, **kwargs):
        super(SavePaymentMethodConfirmationQr, self).__init__(*args, **kwargs)
        if self.type is None or self.type is not ConfirmationType.QR:
            self.type = ConfirmationType.QR

    @property
    def confirmation_data(self):
        """
        Возвращает confirmation_url модели SavePaymentMethodConfirmationQr.

        :return: confirmation_url модели SavePaymentMethodConfirmationQr.
        :rtype: str
        """
        return self.__confirmation_data

    @confirmation_data.setter
    def confirmation_data(self, value):
        """
        Устанавливает confirmation_url модели SavePaymentMethodConfirmationQr.

        :param value: confirmation_url модели SavePaymentMethodConfirmationQr.
        :type value: str
        """
        self.__confirmation_data = value
