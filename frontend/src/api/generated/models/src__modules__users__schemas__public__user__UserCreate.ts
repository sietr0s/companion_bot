/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Схема создания профиля.
 *
 * auth_id НЕ входит в схему — он пробрасывается из JWT-токена.
 * Все остальные поля профиля опциональны.
 */
export type src__modules__users__schemas__public__user__UserCreate = {
    first_name?: (string | null);
    last_name?: (string | null);
    avatar_url?: (string | null);
    bio?: (string | null);
};

