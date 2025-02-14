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
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const reviewApi_1 = require("./reviewApi");
function activate(context) {
    console.log("CodeLens Review Extension is now active!");
    // Register CodeLens provider for ALL files
    let disposable = vscode.languages.registerCodeLensProvider({ scheme: "file", language: "*" }, // Works for all file types
    new CodeReviewProvider());
    context.subscriptions.push(disposable);
    // Register Chat UI Command
    context.subscriptions.push(vscode.commands.registerCommand("codelens.startChat", () => {
        ReviewChatPanel.createOrShow(context.extensionUri);
    }));
}
function deactivate() { }
// CodeLens Provider for Inline Code Reviews
class CodeReviewProvider {
    async provideCodeLenses(document, token) {
        let lenses = [];
        try {
            const reviewResults = await (0, reviewApi_1.submitReview)(document.languageId, document.fileName, document.getText(), null);
            if (!reviewResults || !reviewResults.reviews) {
                return lenses;
            }
            reviewResults.reviews.forEach((review) => {
                const position = new vscode.Position(0, 0);
                const range = new vscode.Range(position, position);
                const command = {
                    title: `🔍 Review: ${review.category} - ${review.message}`,
                    command: "codelens.startChat",
                    arguments: [review]
                };
                lenses.push(new vscode.CodeLens(range, command));
            });
        }
        catch (error) {
            vscode.window.showErrorMessage(`Error fetching code review: ${error}`);
        }
        return lenses;
    }
}
// Review Chat Panel Webview
class ReviewChatPanel {
    static currentPanel;
    _panel;
    _disposables = [];
    static createOrShow(extensionUri) {
        if (ReviewChatPanel.currentPanel) {
            ReviewChatPanel.currentPanel._panel.reveal(vscode.ViewColumn.Two);
            return;
        }
        const panel = vscode.window.createWebviewPanel("reviewChat", "Code Review Chat", vscode.ViewColumn.Two, {
            enableScripts: true
        });
        ReviewChatPanel.currentPanel = new ReviewChatPanel(panel, extensionUri);
    }
    constructor(panel, extensionUri) {
        this._panel = panel;
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.html = this._getHtmlForWebview();
        this._panel.webview.onDidReceiveMessage(async (message) => {
            if (message.command === "sendFeedback") {
                const success = await (0, reviewApi_1.sendFeedback)(message.reviewId, [{ category: message.category, feedback: message.feedback }]);
                this._panel.webview.postMessage({ command: "feedbackReceived", success });
            }
        }, null, this._disposables);
    }
    _getHtmlForWebview() {
        return `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Code Review Chat</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 10px; }
                .chat-container { height: 300px; border: 1px solid #ccc; overflow-y: auto; padding: 10px; }
            </style>
        </head>
        <body>
            <h3>Code Review Feedback</h3>
            <div class="chat-container" id="chatContainer">
                <p><b>LLM Review:</b> <span id="reviewMessage">Waiting for review...</span></p>
            </div>
            <button onclick="sendFeedback('Good')">👍 Good</button>
            <button onclick="sendFeedback('Bad')">👎 Bad</button>

            <script>
                const vscode = acquireVsCodeApi();
                function sendFeedback(feedback) {
                    vscode.postMessage({ command: "sendFeedback", reviewId: "abc123", category: "NULLチェック", feedback });
                }

                window.addEventListener("message", event => {
                    if (event.data.command === "feedbackReceived") {
                        alert("Feedback sent successfully!");
                    }
                });
            </script>
        </body>
        </html>`;
    }
    dispose() {
        ReviewChatPanel.currentPanel = undefined;
        this._panel.dispose();
        this._disposables.forEach(item => item.dispose());
    }
}
//# sourceMappingURL=extension.js.map