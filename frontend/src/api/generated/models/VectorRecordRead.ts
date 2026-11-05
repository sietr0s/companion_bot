/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type VectorRecordRead = {
    id: string;
    conversation_id: string;
    text: string;
    kind?: string;
    embedding?: (Array<number> | null);
    seq_from: number;
    seq_to: number;
    partial?: boolean;
    created_at: string;
    updated_at: string;
};

