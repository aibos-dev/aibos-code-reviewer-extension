import * as vscode from "vscode";
import { sendFeedback, submitReview } from "./reviewApi";

export function activate(context: vscode.ExtensionContext) {
    console.log("CodeLens Review Extension is now active!");

    // Register CodeLens provider
    let disposable = vscode.languages.registerCodeLensProvider(
        { scheme: "file", language: "cpp" }, // Adjust for more languages
        new CodeReviewProvider()
    );
    context.subscriptions.push(disposable);

    // Register Chat UI Command
    context.subscriptions.push(
        vscode.commands.registerCommand("codereview.startChat", () => {
            ReviewChatPanel.createOrShow(context.extensionUri);
        })
    );
}

export function deactivate() {}

class CodeReviewProvider implements vscode.CodeLensProvider {
    async provideCodeLenses(
        document: vscode.TextDocument,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeLens[]> {
        let lenses: vscode.CodeLens[] = [];

        try {
            const reviewResults = await submitReview(
                document.languageId,
                document.fileName,
                document.getText(),
                null
            );

            if (!reviewResults || !reviewResults.reviews) {
                vscode.window.showWarningMessage("No review results received.");
                return lenses;
            }

            reviewResults.reviews.forEach((review: any) => {
                const position = new vscode.Position(0, 0);
                const range = new vscode.Range(position, position);
                const command: vscode.Command = {
                    title: `🔍 Review: ${review.category} - ${review.message}`,
                    command: "codereview.startChat",
                    arguments: [review]
                };
                lenses.push(new vscode.CodeLens(range, command));
            });
        } catch (error) {
            vscode.window.showErrorMessage(`Error fetching code review: ${error}`);
        }

        return lenses;
    }
}

class ReviewChatPanel {
    public static currentPanel: ReviewChatPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(extensionUri: vscode.Uri) {
        if (ReviewChatPanel.currentPanel) {
            ReviewChatPanel.currentPanel._panel.reveal(vscode.ViewColumn.Two);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            "reviewChat",
            "Code Review Chat",
            vscode.ViewColumn.Two,
            {
                enableScripts: true
            }
        );

        ReviewChatPanel.currentPanel = new ReviewChatPanel(panel, extensionUri);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
        this._panel.webview.html = this._getHtmlForWebview();

        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                if (message.command === "sendFeedback") {
                    const success = await sendFeedback(message.reviewId, [{ category: message.category, feedback: message.feedback }]);
                    this._panel.webview.postMessage({ command: "feedbackReceived", success });
                }
            },
            null,
            this._disposables
        );
    }

    private _getHtmlForWebview(): string {
        return `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Code Review Chat</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 10px; }
                .chat-container { display: flex; flex-direction: column; height: 300px; border: 1px solid #ccc; overflow-y: auto; padding: 10px; }
                .chat-message { margin-bottom: 10px; }
                .feedback-buttons { margin-top: 10px; }
            </style>
        </head>
        <body>
            <h3>Code Review Feedback</h3>
            <div class="chat-container" id="chatContainer">
                <p><b>LLM Review:</b> <span id="reviewMessage">Waiting for review...</span></p>
            </div>
            <div class="feedback-buttons">
                <button onclick="sendFeedback('Good')">👍 Good</button>
                <button onclick="sendFeedback('Bad')">👎 Bad</button>
            </div>

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

    public dispose() {
        ReviewChatPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const item = this._disposables.pop();
            if (item) {
                item.dispose();
            }
        }
    }
}
