/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CategoryCreate } from '../models/CategoryCreate';
import type { CategoryRead } from '../models/CategoryRead';
import type { CategoryUpdate } from '../models/CategoryUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ClassifierService {
    /**
     * Список категорий
     * Получить список всех категорий.
     * @returns CategoryRead Successful Response
     * @throws ApiError
     */
    public static getCategoriesApiV1PublicClassifierCategoriesGet(): CancelablePromise<Array<CategoryRead>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/classifier/categories',
        });
    }
    /**
     * Создать категорию
     * Создать новую категорию для классификации.
     * @param requestBody
     * @returns CategoryRead Successful Response
     * @throws ApiError
     */
    public static createCategoryApiV1PublicClassifierCategoriesPost(
        requestBody: CategoryCreate,
    ): CancelablePromise<CategoryRead> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/classifier/categories',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Обновить категорию
     * Обновить категорию по slug.
     * @param slug
     * @param requestBody
     * @returns CategoryRead Successful Response
     * @throws ApiError
     */
    public static updateCategoryApiV1PublicClassifierCategoriesSlugPatch(
        slug: string,
        requestBody: CategoryUpdate,
    ): CancelablePromise<CategoryRead> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/public/classifier/categories/{slug}',
            path: {
                'slug': slug,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Удалить категорию
     * Удалить категорию по slug.
     * @param slug
     * @returns void
     * @throws ApiError
     */
    public static deleteCategoryApiV1PublicClassifierCategoriesSlugDelete(
        slug: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/classifier/categories/{slug}',
            path: {
                'slug': slug,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
