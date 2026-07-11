/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { NotificationLogRead } from '../models/NotificationLogRead';
import type { PaginatedResponse_NotificationLogRead_ } from '../models/PaginatedResponse_NotificationLogRead_';
import type { PaginatedResponse_TemplateRead_ } from '../models/PaginatedResponse_TemplateRead_';
import type { TemplateCreate } from '../models/TemplateCreate';
import type { TemplateRead } from '../models/TemplateRead';
import type { TemplateUpdate } from '../models/TemplateUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class NotificationsService {
    /**
     * Создать шаблон уведомления
     * Создать шаблон уведомления.
     * @param requestBody
     * @returns TemplateRead Successful Response
     * @throws ApiError
     */
    public static createTemplateApiV1PublicNotificationsTemplatesPost(
        requestBody: TemplateCreate,
    ): CancelablePromise<TemplateRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/notifications/templates/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Список шаблонов
     * Получить список шаблонов с фильтрацией и пагинацией.
     * @param filters field+operator+value
     * @param page
     * @param limit
     * @returns PaginatedResponse_TemplateRead_ Successful Response
     * @throws ApiError
     */
    public static getTemplatesApiV1PublicNotificationsTemplatesGet(
        filters?: Array<string>,
        page: number = 1,
        limit: number = 100,
    ): CancelablePromise<PaginatedResponse_TemplateRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/notifications/templates/',
            query: {
                'filters': filters,
                'page': page,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Получить шаблон по ID
     * Получить шаблон по ID.
     * @param templateId
     * @returns TemplateRead Successful Response
     * @throws ApiError
     */
    public static getTemplateApiV1PublicNotificationsTemplatesTemplateIdGet(
        templateId: string,
    ): CancelablePromise<TemplateRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/notifications/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Обновить шаблон
     * Обновить шаблон.
     * @param templateId
     * @param requestBody
     * @returns TemplateRead Successful Response
     * @throws ApiError
     */
    public static updateTemplateApiV1PublicNotificationsTemplatesTemplateIdPatch(
        templateId: string,
        requestBody: TemplateUpdate,
    ): CancelablePromise<TemplateRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/notifications/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Удалить шаблон
     * Удалить шаблон.
     * @param templateId
     * @returns void
     * @throws ApiError
     */
    public static deleteTemplateApiV1PublicNotificationsTemplatesTemplateIdDelete(
        templateId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/notifications/templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * История уведомлений
     * Получить историю уведомлений с фильтрацией и пагинацией.
     * @param filters field+operator+value
     * @param page
     * @param limit
     * @returns PaginatedResponse_NotificationLogRead_ Successful Response
     * @throws ApiError
     */
    public static getHistoryApiV1PublicNotificationsHistoryGet(
        filters?: Array<string>,
        page: number = 1,
        limit: number = 50,
    ): CancelablePromise<PaginatedResponse_NotificationLogRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/notifications/history/',
            query: {
                'filters': filters,
                'page': page,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Детальный просмотр лога уведомления
     * Получить детальную информацию о уведомлении.
     * @param logId
     * @returns NotificationLogRead Successful Response
     * @throws ApiError
     */
    public static getHistoryEntryApiV1PublicNotificationsHistoryLogIdGet(
        logId: string,
    ): CancelablePromise<NotificationLogRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/notifications/history/{log_id}',
            path: {
                'log_id': logId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
