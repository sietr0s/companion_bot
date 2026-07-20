/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PaginatedResponse_JobOfferAdminRead_ } from '../models/PaginatedResponse_JobOfferAdminRead_';
import type { PaginatedResponse_SubscriptionAdminRead_ } from '../models/PaginatedResponse_SubscriptionAdminRead_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class JobMatcherService {
    /**
     * Получить подписки для администратора
     * Вернуть подписки только авторизованному администратору.
     * @param filters field+operator+value
     * @param page
     * @param limit
     * @param orderBy Поле сортировки; '-' = DESC
     * @returns PaginatedResponse_SubscriptionAdminRead_ Successful Response
     * @throws ApiError
     */
    public static getSubscriptionsAdminApiV1PublicJobMatcherSubscriptionsGet(
        filters?: Array<string>,
        page: number = 1,
        limit: number = 100,
        orderBy: string = '-created_at',
    ): CancelablePromise<PaginatedResponse_SubscriptionAdminRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/job-matcher/subscriptions',
            query: {
                'filters': filters,
                'page': page,
                'limit': limit,
                'order_by': orderBy,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Получить вакансии для администратора
     * Вернуть сохранённые вакансии авторизованному администратору.
     * @param filters field+operator+value
     * @param page
     * @param limit
     * @param orderBy Поле сортировки; '-' = DESC
     * @returns PaginatedResponse_JobOfferAdminRead_ Successful Response
     * @throws ApiError
     */
    public static getOffersAdminApiV1PublicJobMatcherOffersGet(
        filters?: Array<string>,
        page: number = 1,
        limit: number = 50,
        orderBy: string = '-created_at',
    ): CancelablePromise<PaginatedResponse_JobOfferAdminRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/job-matcher/offers',
            query: {
                'filters': filters,
                'page': page,
                'limit': limit,
                'order_by': orderBy,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Удалить пользователя и его подписку
     * Удалить подписку и через межмодульные клиенты удалить user и auth.
     * @param authId
     * @returns void
     * @throws ApiError
     */
    public static deleteUserAdminApiV1PublicJobMatcherUsersAuthIdDelete(
        authId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/job-matcher/users/{auth_id}',
            path: {
                'auth_id': authId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
