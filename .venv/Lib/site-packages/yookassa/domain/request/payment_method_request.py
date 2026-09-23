# coding: utf-8
from yookassa.domain.common import RequestObject, TypeFactory, DataContext
from yookassa.domain.models.confirmation.request.confirmation_request import ConfirmationRequest
from yookassa.domain.models.payment_data.request.credit_card import CreditCard
from yookassa.domain.models.payment_method import SavePaymentMethodConfirmationFactory, SavePaymentMethodHolder
from yookassa.domain.models import SavePaymentMethodType


class SavePaymentMethodDataRequest(RequestObject):
    """
    Данные для проверки и сохранения способа оплаты.
    """  # noqa: E501

    __type = None
    """Код способа оплаты."""  # noqa: E501

    __holder = None
    """Данные магазина, для которого сохраняется способ оплаты."""  # noqa: E501

    __client_ip = None
    """IPv4 или IPv6-адрес пользователя."""  # noqa: E501

    __confirmation = None
    """Данные, необходимые для инициирования сценария подтверждения привязки."""  # noqa: E501

    __metadata = None
    """Любые дополнительные данные."""  # noqa: E501

    @property
    def type(self):
        """
        Возвращает type модели SavePaymentMethodDataRequest.

        :return: type модели SavePaymentMethodDataRequest.
        :rtype: str
        """
        return self.__type

    @type.setter
    def type(self, value):
        """
        Устанавливает type модели SavePaymentMethodDataRequest.

        :param value: type модели SavePaymentMethodDataRequest.
        :type value: str
        """
        if value is None:  # noqa: E501
            raise ValueError("Invalid value for `type`, must not be `None`")  # noqa: E501
        self.__type = str(value)

    @property
    def holder(self):
        """
        Возвращает holder модели SavePaymentMethodDataRequest.

        :return: holder модели SavePaymentMethodDataRequest.
        :rtype: dict
        """
        return self.__holder

    @holder.setter
    def holder(self, value):
        """
        Устанавливает holder модели SavePaymentMethodDataRequest.

        :param value: holder модели SavePaymentMethodDataRequest.
        :type value: dict
        """
        if isinstance(value, dict):
            self.__holder = SavePaymentMethodHolder(value)
        elif isinstance(value, SavePaymentMethodHolder):
            self.__holder = value
        else:
            raise TypeError('Invalid holder value type')

    @property
    def client_ip(self):
        """
        Возвращает client_ip модели SavePaymentMethodDataRequest.

        :return: client_ip модели SavePaymentMethodDataRequest.
        :rtype: str
        """
        return self.__client_ip

    @client_ip.setter
    def client_ip(self, value):
        """
        Устанавливает client_ip модели SavePaymentMethodDataRequest.

        :param value: client_ip модели SavePaymentMethodDataRequest.
        :type value: str
        """
        cast_value = str(value)
        if cast_value:
            self.__client_ip = cast_value

    @property
    def confirmation(self):
        """
        Возвращает confirmation модели SavePaymentMethodDataRequest.

        :return: confirmation модели SavePaymentMethodDataRequest.
        :rtype: object
        """
        return self.__confirmation

    @confirmation.setter
    def confirmation(self, value):
        """
        Устанавливает confirmation модели SavePaymentMethodDataRequest.

        :param value: confirmation модели SavePaymentMethodDataRequest.
        :type value: object
        """
        if isinstance(value, dict):
            self.__confirmation = SavePaymentMethodConfirmationFactory().create(value, self.context())
        elif isinstance(value, ConfirmationRequest):
            self.__confirmation = value
        else:
            raise TypeError('Invalid confirmation data type in PaymentMethodRequest.confirmation')

    @property
    def metadata(self):
        """
        Возвращает metadata модели SavePaymentMethodDataRequest.

        :return: metadata модели SavePaymentMethodDataRequest.
        :rtype: dict[str, str]
        """
        return self.__metadata

    @metadata.setter
    def metadata(self, value):
        """
        Устанавливает metadata модели SavePaymentMethodDataRequest.

        :param value: metadata модели SavePaymentMethodDataRequest.
        :type value: dict[str, str]
        """
        if type(value) is dict:
            self.__metadata = value

    def validate(self):
        """
        Валидация данных модели PaymentMethodRequest.
        """
        if not self.type:
            self.__set_validation_error('Payment method type not specified')

    def __set_validation_error(self, message):
        """
        Устанавливает message в Exception при валидации модели SavePaymentMethodDataRequest.

        :param message: message модели Exception.
        :type message: str
        """
        raise ValueError(message)


class SavePaymentMethodDataBankCardRequest(SavePaymentMethodDataRequest):
    """Данные для проверки и сохранения способа оплаты."""  # noqa: E501

    __card = None
    """Данные банковской карты."""

    """
    Данные для проверки и сохранения счета СБП.
    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        super(SavePaymentMethodDataBankCardRequest, self).__init__(*args, **kwargs)
        if self.type is None or self.type is not SavePaymentMethodType.BANK_CARD:
            self.type = SavePaymentMethodType.BANK_CARD


    @property
    def card(self):
        """Возвращает card модели SavePaymentMethodDataRequestBankCardRequest.

        :return: card модели SavePaymentMethodDataRequestBankCardRequest.
        :rtype: CreditCard
        """
        return self.__card

    @card.setter
    def card(self, value):
        """Устанавливает card модели SavePaymentMethodDataRequestBankCardRequest.

        :param value: card модели SavePaymentMethodDataRequestBankCardRequest.
        :type value: CreditCard
        """
        if isinstance(value, dict):
            self.__card = CreditCard(value)
        elif isinstance(value, CreditCard):
            self.__card = value
        else:
            raise TypeError('Invalid card value type')


class SavePaymentMethodDataSbpRequest(SavePaymentMethodDataRequest):
    """
    Данные для проверки и сохранения счета СБП.
    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        super(SavePaymentMethodDataSbpRequest, self).__init__(*args, **kwargs)
        if self.type is None or self.type is not SavePaymentMethodType.SBP:
            self.type = SavePaymentMethodType.SBP


class SavePaymentMethodRequestClassMap(DataContext):
    """
    Сопоставление классов PaymentMethodRequest по типу.
    """  # noqa: E501

    def __init__(self):
        super(SavePaymentMethodRequestClassMap, self).__init__(('request'))

    @property
    def request(self):
        return {
            SavePaymentMethodType.BANK_CARD: SavePaymentMethodDataBankCardRequest,
            SavePaymentMethodType.SBP: SavePaymentMethodDataSbpRequest,
        }


class SavePaymentMethodRequestFactory(TypeFactory):
    """
    Фабрика создания объекта PaymentMethodRequest по типу.
    """  # noqa: E501

    def __init__(self):
        super(SavePaymentMethodRequestFactory, self).__init__(SavePaymentMethodRequestClassMap())
