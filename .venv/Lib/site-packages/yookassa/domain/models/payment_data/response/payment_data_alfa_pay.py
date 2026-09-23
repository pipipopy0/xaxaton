# -*- coding: utf-8 -*-
from yookassa.domain.common.payment_method_type import PaymentMethodType
from yookassa.domain.models.payment_data.payment_data import ResponsePaymentData
from yookassa.domain.models.payment_data.response.credit_card import CreditCard


class PaymentDataAlfaPay(ResponsePaymentData):
    """
    Данные для оплаты через Alfa Pay.
    """  # noqa: E501

    __card = None
    """Данные банковской карты."""  # noqa: E501

    def __init__(self, *args, **kwargs):
        super(PaymentDataAlfaPay, self).__init__(*args, **kwargs)
        if self.type is None or self.type is not PaymentMethodType.ALFA_PAY:
            self.type = PaymentMethodType.ALFA_PAY

    @property
    def card(self):
        """
        Возвращает card модели PaymentDataAlfaPay.

        :return: card модели PaymentDataAlfaPay.
        :rtype: CreditCard
        """
        return self.__card

    @card.setter
    def card(self, value):
        """
        Устанавливает card модели PaymentDataAlfaPay.

        :param value: card модели PaymentDataAlfaPay.
        :type value: CreditCard
        """
        if isinstance(value, dict):
            self.__card = CreditCard(value)
        elif isinstance(value, CreditCard):
            self.__card = value
        else:
            raise TypeError('Invalid card value type in PaymentDataAlfaPay')
