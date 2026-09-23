# -*- coding: utf-8 -*-
from yookassa.domain.common import ConfirmationType
from yookassa.domain.models.payment_method import SavePaymentMethodConfirmation


class SavePaymentMethodConfirmationQr(SavePaymentMethodConfirmation):
    """
    Сценарий, при котором необходимо отправить плательщика на веб-страницу ЮKassa или партнера для подтверждения платежа.
    """  # noqa: E501

    __return_url = None
    """URL, на который вернется пользователь после подтверждения или отмены платежа на веб-странице. Не более 2048 символов."""  # noqa: E501

    def __init__(self, *args, **kwargs):
        super(SavePaymentMethodConfirmationQr, self).__init__(*args, **kwargs)
        if self.type is None or self.type is not ConfirmationType.QR:
            self.type = ConfirmationType.QR

    @property
    def return_url(self):
        """
        Возвращает return_url модели SavePaymentMethodConfirmationQr.

        :return: return_url модели SavePaymentMethodConfirmationQr.
        :rtype: str
        """
        return self.__return_url

    @return_url.setter
    def return_url(self, value):
        """
        Устанавливает return_url модели SavePaymentMethodConfirmationQr.

        :param value: return_url модели SavePaymentMethodConfirmationQr.
        :type value: str
        """
        cast_value = str(value)
        if cast_value:
            self.__return_url = cast_value
        else:
            raise ValueError('Invalid returnUrl value')
