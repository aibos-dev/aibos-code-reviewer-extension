"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.submitReview = submitReview;
exports.sendFeedback = sendFeedback;
const axios_1 = __importDefault(require("axios"));
const vscode = __importStar(require("vscode"));
const API_BASE_URL = "http://localhost:5000/v1";
async function submitReview(language, fileName, sourceCode, diff) {
    try {
        const response = await axios_1.default.post(`${API_BASE_URL}/review`, {
            language,
            fileName,
            sourceCode,
            diff,
            options: { level: "function" }
        });
        return response.data;
    }
    catch (error) {
        const errorMessage = error.message;
        vscode.window.showErrorMessage(`Code Review API Error: ${errorMessage}`);
        return null;
    }
}
async function sendFeedback(reviewId, feedbacks) {
    try {
        const response = await axios_1.default.post(`${API_BASE_URL}/review/feedback`, {
            reviewId,
            feedbacks
        });
        return response.data.result === "success";
    }
    catch (error) {
        const errorMessage = error.message;
        vscode.window.showErrorMessage(`Feedback API Error: ${errorMessage}`);
        return false;
    }
}
//# sourceMappingURL=reviewApi.js.map