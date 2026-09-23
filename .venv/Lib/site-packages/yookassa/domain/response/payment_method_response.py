# coding: utf-8
import datetime
import re  # noqa: F401

from yookassa.domain.common import ResponseObject
from yookassa.domain.models.payment_data.response.credit_card import CreditCard
from yookassa.domain.models.payment_method import SavePaymentMethodConfirmationFactory
from yookassa.domain.models.payment_method.response import SavePaymentMethodHolder, SavePaymentMethodSbpPayerBankDetails
from yookassa.domain.models.payment_method.save_payment_method_type import SavePaymentMethodType


class SavePaymentMethodResponse(ResponseObject):
    """Сохраненный способ оплаты."""  # noqa: E501

    __id = None
    """Идентификатор сохраненного способа оплаты."""  # noqa: E501

    __type = None
    """Код способа оплаты. Возможное значение: * ~`bank_card` — банковская карта."""  # noqa: E501

    __saved = None
    """Признак сохранения способа оплаты для %[автоплатежей](/developers/payment-acceptance/scenario-extensions/recurring-payments/pay-with-saved).  Возможные значения:   * ~`true` — способ оплаты сохранен для автоплатежей и выплат; * ~`false` — способ оплаты не сохранен. """  # noqa: E501

    __status = None
    """Статус проверки и сохранения способа оплаты."""  # noqa: E501

    __holder = None
    """Данные магазина, для которого сохраняется способ оплаты."""  # noqa: E501

    __title = None
    """Название способа оплаты."""  # noqa: E501

    __confirmation = None
    """Выбранный сценарий подтверждения привязки. Присутствует, когда привязка ожидает подтверждения от пользователя."""  # noqa: E501

    __metadata = None
    """Любые дополнительные данные, которые нужны вам для работы (например, ваш внутренний идентификатор заказа). Передаются в виде набора пар «ключ-значение» и возвращаются в ответе от ЮKassa. Ограничения: максимум 16 ключей, имя ключа не больше 32 символов, значение ключа не больше 512 символов, тип данных — строка в формате UTF-8. """  # noqa: E501


    @property
    def id(self):
        """Возвращает id модели SavePaymentMethodResponse.

        :return: id модели SavePaymentMethodResponse.
        :rtype: str
        """
        return self.__id

    @id.setter
    def id(self, value):
        """Устанавливает id модели SavePaymentMethodResponse.

        :param value: id модели SavePaymentMethodResponse.
        :type value: str
        """
        self.__id = value

    @property
    def type(self):
        """Возвращает type модели SavePaymentMethodResponse.

        :return: type модели SavePaymentMethodResponse.
        :rtype: str
        """
        return self.__type

    @type.setter
    def type(self, value):
        """Устанавливает type модели SavePaymentMethodResponse.

        :param value: type модели SavePaymentMethodResponse.
        :type value: str
        """
        self.__type = value

    @property
    def saved(self):
        """Возвращает saved модели SavePaymentMethodResponse.

        :return: saved модели SavePaymentMethodResponse.
        :rtype: bool
        """
        return self.__saved

    @saved.setter
    def saved(self, value):
        """Устанавливает saved модели SavePaymentMethodResponse.

        :param value: saved модели SavePaymentMethodResponse.
        :type value: bool
        """
        self.__saved = value

    @property
    def status(self):
        """Возвращает status модели SavePaymentMethodResponse.

        :return: status модели SavePaymentMethodResponse.
        :rtype: str
        """
        return self.__status

    @status.setter
    def status(self, value):
        """Устанавливает status модели SavePaymentMethodResponse.

        :param value: status модели SavePaymentMethodResponse.
        :type value: str
        """
        self.__status = value

    @property
    def holder(self):
        """Возвращает holder модели SavePaymentMethodResponse.

        :return: holder модели SavePaymentMethodResponse.
        :rtype: SavePaymentMethodHolder
        """
        return self.__holder

    @holder.setter
    def holder(self, value):
        """Устанавливает holder модели SavePaymentMethodResponse.

        :param value: holder модели SavePaymentMethodResponse.
        :type value: SavePaymentMethodHolder
        """
        self.__holder = SavePaymentMethodHolder(value)

    @property
    def title(self):
        """Возвращает title модели SavePaymentMethodResponse.

        :return: title модели SavePaymentMethodResponse.
        :rtype: str
        """
        return self.__title

    @title.setter
    def title(self, value):
        """Устанавливает title модели SavePaymentMethodResponse.

        :param value: title модели SavePaymentMethodResponse.
        :type value: str
        """
        self.__title = value

    @property
    def confirmation(self):
        """Возвращает confirmation модели SavePaymentMethodResponse.

        :return: confirmation модели SavePaymentMethodResponse.
        :rtype: ConfirmationResponse
        """
        return self.__confirmation

    @confirmation.setter
    def confirmation(self, value):
        """Устанавливает confirmation модели SavePaymentMethodResponse.

        :param value: confirmation модели SavePaymentMethodResponse.
        :type value: ConfirmationResponse
        """
        self.__confirmation = SavePaymentMethodConfirmationFactory().create(value, self.context())

    @property
    def metadata(self):
        """Возвращает metadata модели SavePaymentMethodResponse.

        :return: metadata модели SavePaymentMethodResponse.
        :rtype: dict[str, str]
        """
        return self.__metadata

    @metadata.setter
    def metadata(self, value):
        """Устанавливает metadata модели SavePaymentMethodResponse.

        :param value: metadata модели SavePaymentMethodResponse.
        :type value: dict[str, str]
        """
        if value is not None and len(value) > 16:
            raise ValueError("Invalid value for `metadata`, number of items must be less than or equal to `16`")  # noqa: E501
        self.__metadata = value


class SavePaymentMethodBankCardResponse(SavePaymentMethodResponse):
    """Данные для проверки и сохранения банковской карты."""  # noqa: E501

    __card = None
    """Данные банковской карты."""

    """
    Данные для проверки и сохранения счета СБП.
    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        super(SavePaymentMethodBankCardResponse, self).__init__(*args, **kwargs)
        if self.type is None or self.type is not SavePaymentMethodType.BANK_CARD:
            self.type = SavePaymentMethodType.BANK_CARD


    @property
    def card(self):
        """Возвращает card модели SavePaymentMethodRequestBankCardResponse.

        :return: card модели SavePaymentMethodRequestBankCardResponse.
        :rtype: CreditCard
        """
        return self.__card

    @card.setter
    def card(self, value):
        """Устанавливает card модели SavePaymentMethodRequestBankCardResponse.

        :param value: card модели SavePaymentMethodRequestBankCardResponse.
        :type value: CreditCard
        """
        self.__card = CreditCard(value)


class SavePaymentMethodSbpResponse(SavePaymentMethodResponse):
    """Данные для проверки и сохранения счета СБП."""  # noqa: E501

    __payer_bank_details = None
    """
    Данные для проверки и сохранения счета СБП.
    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        super(SavePaymentMethodSbpResponse, self).__init__(*args, **kwargs)
        if self.type is None or self.type is not SavePaymentMethodType.SBP:
            self.type = SavePaymentMethodType.SBP

    @property
    def payer_bank_details(self):
        """Возвращает payer_bank_details модели SavePaymentMethodSbpResponse.

        :return: payer_bank_details модели SavePaymentMethodSbpResponse.
        :rtype: SavePaymentMethodSbpPayerBankDetails
        """
        return self.__payer_bank_details

    @payer_bank_details.setter
    def payer_bank_details(self, value):
        """Устанавливает payer_bank_details модели SavePaymentMethodSbpResponse.

        :param value: payer_bank_details модели SavePaymentMethodSbpResponse.
        :type value: SavePaymentMethodSbpPayerBankDetails
        """

        self.__payer_bank_details = SavePaymentMethodSbpPayerBankDetails(value)
