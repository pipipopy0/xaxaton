# -*- coding: utf-8 -*-
from yookassa.domain.common.type_factory import TypeFactory
from yookassa.domain.models.payment_method import SavePaymentMethodConfirmationClassMap


class SavePaymentMethodConfirmationFactory(TypeFactory):
    """
    Фабрика создания объекта PaymentMethodConfirmation по типу.
    """  # noqa: E501

    def __init__(self):
        super(SavePaymentMethodConfirmationFactory, self).__init__(SavePaymentMethodConfirmationClassMap())
