# -*- coding: utf-8 -*-
from yookassa.domain.common.confirmation_type import ConfirmationType
from yookassa.domain.common.data_context import DataContext
from yookassa.domain.models.payment_method.request import \
    SavePaymentMethodConfirmationRedirect as RequestPaymentMethodConfirmationRedirect, \
    SavePaymentMethodConfirmationQr as RequestPaymentMethodConfirmationQr
from yookassa.domain.models.payment_method.response import \
    SavePaymentMethodConfirmationRedirect as ResponsePaymentMethodConfirmationRedirect, \
    SavePaymentMethodConfirmationQr as ResponsePaymentMethodConfirmationQr


class SavePaymentMethodConfirmationClassMap(DataContext):
    """
    Сопоставление классов PaymentMethodConfirmation по типу.
    """  # noqa: E501

    def __init__(self):
        super(SavePaymentMethodConfirmationClassMap, self).__init__(('request', 'response'))

    @property
    def request(self):
        return {
            ConfirmationType.REDIRECT: RequestPaymentMethodConfirmationRedirect,
            ConfirmationType.QR: RequestPaymentMethodConfirmationQr,
        }

    @property
    def response(self):
        return {
            ConfirmationType.REDIRECT: ResponsePaymentMethodConfirmationRedirect,
            ConfirmationType.QR: ResponsePaymentMethodConfirmationQr,
        }
