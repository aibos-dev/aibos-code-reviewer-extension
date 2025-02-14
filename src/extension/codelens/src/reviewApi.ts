import axios from "axios";
import * as vscode from "vscode";

const API_BASE_URL = "http://localhost:5000/v1";

export async function submitReview(
    language: string,
    fileName: string,
    sourceCode: string,
    diff: string | null
): Promise<any> {
    try {
        const response = await axios.post(`${API_BASE_URL}/review`, {
            language,
            fileName,
            sourceCode,
            diff,
            options: { level: "function" }
        });

        return response.data;
    } catch (error) {
        const errorMessage = (error as any).message;
        vscode.window.showErrorMessage(`Code Review API Error: ${errorMessage}`);
        return null;
    }
}

export async function sendFeedback(
    reviewId: string,
    feedbacks: { category: string; feedback: string }[]
): Promise<boolean> {
    try {
        const response = await axios.post(`${API_BASE_URL}/review/feedback`, {
            reviewId,
            feedbacks
        });

        return response.data.result === "success";
    } catch (error) {
        const errorMessage = (error as any).message;
        vscode.window.showErrorMessage(`Feedback API Error: ${errorMessage}`);
        return false;
    }
}
