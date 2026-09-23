# -*- coding: utf-8 -*-
import uuid

from yookassa.client import ApiClient
from yookassa.domain.common.http_verb import HttpVerb
from yookassa.domain.request import CreatePosLinkRequest, RecipientPosLinkRequest
from yookassa.domain.response import PosLinkResponse


class PosLink:
    """
    Класс, представляющий модель PosLink.
    """  # noqa: E501

    base_path = '/pos_links'

    def __init__(self):
        self.client = ApiClient()

    @classmethod
    def create(cls, params, idempotency_key=None):
        """
        Активация кассовой ссылки

        :param params: Данные передаваемые в API
        :param idempotency_key: Ключ идемпотентности
        :return: PosLinkResponse Объект ответа, возвращаемого API при запросе кассовой ссылки
        """
        instance = cls()
        path = cls.base_path

        if not idempotency_key:
            idempotency_key = uuid.uuid4()

        headers = {
            'Idempotence-Key': str(idempotency_key)
        }

        if isinstance(params, dict):
            params_object = CreatePosLinkRequest(params)
        elif isinstance(params, CreatePosLinkRequest):
            params_object = params
        else:
            raise TypeError('Invalid params value type')

        response = instance.client.request(HttpVerb.POST, path, None, headers, params_object)
        return PosLinkResponse(response)

    @classmethod
    def find_one(cls, pos_link_id):
        """
        Возвращает информацию о кассовой ссылке

        :param pos_link_id: Уникальный идентификатор кассовой ссылки
        :return: PosLinkResponse Объект ответа, возвращаемого API при запросе кассовой ссылки
        """
        instance = cls()
        if not isinstance(pos_link_id, str) or not pos_link_id:
            raise ValueError('Invalid pos_link_id value')

        path = instance.base_path + '/' + pos_link_id
        response = instance.client.request(HttpVerb.GET, path)
        return PosLinkResponse(response)

    @classmethod
    def activate(cls, pos_link_id, idempotency_key=None):
        """
        Активация ранее деактивированной кассовой ссылки

        :param pos_link_id: Уникальный идентификатор кассовой ссылки
        :param idempotency_key: Ключ идемпотентности
        :return: PosLinkResponse Объект ответа, возвращаемого API при запросе кассовой ссылки
        """
        instance = cls()
        if not isinstance(pos_link_id, str) or not pos_link_id:
            raise ValueError('Invalid pos_link_id value')

        if not idempotency_key:
            idempotency_key = uuid.uuid4()

        path = instance.base_path + '/' + pos_link_id + '/activate'
        headers = {
            'Idempotence-Key': str(idempotency_key)
        }
        response = instance.client.request(HttpVerb.POST, path, None, headers)
        return PosLinkResponse(response)

    @classmethod
    def deactivate(cls, pos_link_id, idempotency_key=None):
        """
        Деактивация кассовой ссылки

        :param pos_link_id: Уникальный идентификатор кассовой ссылки
        :param idempotency_key: Ключ идемпотентности
        :return: PosLinkResponse Объект ответа, возвращаемого API при запросе кассовой ссылки
        """
        instance = cls()
        if not isinstance(pos_link_id, str) or not pos_link_id:
            raise ValueError('Invalid pos_link_id value')

        if not idempotency_key:
            idempotency_key = uuid.uuid4()

        path = instance.base_path + '/' + pos_link_id + '/deactivate'
        headers = {
            'Idempotence-Key': str(idempotency_key)
        }
        response = instance.client.request(HttpVerb.POST, path, None, headers)
        return PosLinkResponse(response)

    @classmethod
    def change_recipient(cls, pos_link_id, params, idempotency_key=None):
        """
        Изменение торговой точки, привязанной к кассовой ссылке

        :param pos_link_id: Уникальный идентификатор кассовой ссылки
        :param params: Данные передаваемые в API
        :param idempotency_key: Ключ идемпотентности
        :return: PosLinkResponse Объект ответа, возвращаемого API при запросе кассовой ссылки
        """
        instance = cls()
        if not isinstance(pos_link_id, str) or not pos_link_id:
            raise ValueError('Invalid pos_link_id value')

        if not idempotency_key:
            idempotency_key = uuid.uuid4()

        path = instance.base_path + '/' + pos_link_id + '/recipient'
        headers = {
            'Idempotence-Key': str(idempotency_key)
        }

        if isinstance(params, dict):
            params_object = RecipientPosLinkRequest(params)
        elif isinstance(params, RecipientPosLinkRequest):
            params_object = params
        else:
            raise TypeError('Invalid params value type')

        response = instance.client.request(HttpVerb.POST, path, None, headers, params_object)
        return PosLinkResponse(response)
