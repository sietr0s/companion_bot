/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type VectorRecordCreate = {
    conversation_id: string;
    text: string;
    kind?: string;
    embedding?: (Array<number> | null);
    seq_from?: number;
    seq_to?: number;
    partial?: boolean;
};

