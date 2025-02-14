import axios from "axios";
import * as vscode from "vscode";

const API_BASE_URL = "http://localhost:5000/v1"; // Change to your actual API endpoint

/**
 * Submits source code for review.
 * @param language The programming language of the code.
 * @param fileName The file name (optional).
 * @param sourceCode The source code to be reviewed.
 * @param diff The code diff, if applicable.
 * @returns The review response from the API.
 */
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
            options: { level: "function" }, // Review granularity level
        });

        return response.data;
    } catch (error) {
        const err = error as any;
        vscode.window.showErrorMessage(
            `Code Review API Error: ${err.response?.data?.error || err.message}`
        );
        return null;
    }
}

/**
 * Sends user feedback for a review result.
 * @param reviewId The ID of the review.
 * @param feedbacks The feedback array [{ category: "NULLチェック", feedback: "Good" }, ...]
 * @returns API response confirming feedback submission.
 */
export async function sendFeedback(
    reviewId: string,
    feedbacks: { category: string; feedback: string }[]
): Promise<boolean> {
    try {
        const response = await axios.post(`${API_BASE_URL}/review/feedback`, {
            reviewId,
            feedbacks,
        });

        if (response.data.result === "success") {
            vscode.window.showInformationMessage(`Feedback sent successfully.`);
            return true;
        }

        vscode.window.showErrorMessage(`Failed to send feedback.`);
        return false;
    } catch (error) {
        const err = error as any;
        vscode.window.showErrorMessage(
            `Feedback API Error: ${err.response?.data?.error || err.message}`
        );
        return false;
    }
}
