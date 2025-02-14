// src/extension.ts - Main VS Code Extension Entry Point
import * as vscode from 'vscode';
import { sendFeedback, submitReview } from './reviewApi';

export function activate(context: vscode.ExtensionContext) {
	console.log('CodeLens Review Extension is now active!');

	let disposable = vscode.languages.registerCodeLensProvider(
		{ scheme: 'file', language: 'cpp' }, // Adjust for more languages if needed
		new CodeReviewProvider()
	);

	context.subscriptions.push(disposable);

	// Register the command to show details & collect feedback
	context.subscriptions.push(
		vscode.commands.registerCommand('codereview.showDetails', async (review) => {
			const feedback = await vscode.window.showQuickPick(['Good', 'Bad'], { placeHolder: 'Provide feedback' });
			if (feedback) {
				sendFeedback(review.reviewId, [{ category: review.category, feedback }]);
				vscode.window.showInformationMessage(`Feedback submitted: ${feedback}`);
			}
		})
	);
}

export function deactivate() { }

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
				null // No diff available in VS Code API
			);

			if (!reviewResults || !reviewResults.reviews) {
				vscode.window.showWarningMessage("No review results received.");
				return lenses;
			}

			reviewResults.reviews.forEach((review: any) => {
				const position = new vscode.Position(0, 0); // Adjust if needed
				const range = new vscode.Range(position, position);
				const command: vscode.Command = {
					title: `🔍 Review: ${review.category} - ${review.message}`,
					command: 'codereview.showDetails',
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
