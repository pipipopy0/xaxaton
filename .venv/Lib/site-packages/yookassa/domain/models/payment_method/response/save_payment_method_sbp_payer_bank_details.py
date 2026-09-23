# coding: utf-8
from yookassa.domain.common import BaseObject


class SavePaymentMethodSbpPayerBankDetails(BaseObject):
    """Реквизиты счета, который использовался для привязки.  Обязательный параметр для платежей в статусе ~`succeeded`. В остальных случаях может отсутствовать. """  # noqa: E501

    __bank_id = None
    """Идентификатор банка или платежного сервиса в СБП (НСПК)."""  # noqa: E501

    @property
    def bank_id(self):
        """Возвращает bank_id модели SavePaymentMethodSbpPayerBankDetails.

        :return: bank_id модели SavePaymentMethodSbpPayerBankDetails.
        :rtype: str
        """
        return self.__bank_id

    @bank_id.setter
    def bank_id(self, value):
        """Устанавливает bank_id модели SavePaymentMethodSbpPayerBankDetails.

        :param value: bank_id модели SavePaymentMethodSbpPayerBankDetails.
        :type value: str
        """
        self.__bank_id = value
