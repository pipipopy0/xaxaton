# -*- coding: utf-8 -*-
from yookassa.domain.common.payment_method_type import PaymentMethodType
from yookassa.domain.models.payment_data.payment_data import PaymentData


class PaymentDataAlfaPay(PaymentData):
    """
    Данные для оплаты через Alfa Pay.
    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        super(PaymentDataAlfaPay, self).__init__(*args, **kwargs)
        if self.type is None or self.type is not PaymentMethodType.ALFA_PAY:
            self.type = PaymentMethodType.ALFA_PAY
