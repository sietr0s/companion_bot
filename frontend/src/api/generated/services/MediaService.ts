/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_upload_file_api_v1_public_media_upload_post } from '../models/Body_upload_file_api_v1_public_media_upload_post';
import type { FileRead } from '../models/FileRead';
import type { FileUploadResponse } from '../models/FileUploadResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MediaService {
    /**
     * Загрузить файл
     * Загрузить файл (требует JWT).
     * @param formData
     * @returns FileUploadResponse Successful Response
     * @throws ApiError
     */
    public static uploadFileApiV1PublicMediaUploadPost(
        formData: Body_upload_file_api_v1_public_media_upload_post,
    ): CancelablePromise<FileUploadResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/public/media/upload',
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Метаданные файла
     * Получить метаданные файла.
     *
     * Публичные файлы (is_public=True) доступны без авторизации.
     * Приватные файлы возвращают 404.
     * @param fileId
     * @returns FileRead Successful Response
     * @throws ApiError
     */
    public static getFileApiV1PublicMediaFileIdGet(
        fileId: string,
    ): CancelablePromise<FileRead> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/media/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Удалить файл
     * Удалить файл (требует JWT).
     * @param fileId
     * @returns void
     * @throws ApiError
     */
    public static deleteFileApiV1PublicMediaFileIdDelete(
        fileId: string,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/public/media/{file_id}',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Скачать файл
     * Скачать файл (потоком).
     *
     * Публичные файлы (is_public=True) доступны без авторизации.
     * Приватные файлы возвращают 404.
     * @param fileId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static downloadFileApiV1PublicMediaFileIdDownloadGet(
        fileId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/public/media/{file_id}/download',
            path: {
                'file_id': fileId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
