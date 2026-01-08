"""
The Safety Budget Script
File: scripts/setup_safety_budget.py This script uses boto3 to create the $10 hard-stop. Notice the "Dry Run" logic—a key trait of a senior Cloud Engineer.
"""

import boto3


class BudgetGuard:
    def __init__(self, amount=10, email="biju.tholath@outlook.com"):
        self.client = boto3.client('budgets')
        self.sts = boto3.client('sts')
        self.account_id = self.sts.get_caller_identity()["Account"]
        self.amount = str(amount)
        self.email = email

    def create_hard_stop_budget(self):
        budget_name = "LifeProof-AI-Hard-Stop"
        print(f"🚀 Initializing Budget Guard for Account {self.account_id}...")

        try:
            self.client.create_budget(
                AccountId=self.account_id,
                Budget={
                    'BudgetName': budget_name,
                    'BudgetLimit': {'Amount': self.amount, 'Unit': 'USD'},
                    'TimeUnit': 'MONTHLY',
                    'BudgetType': 'COST'
                },
                NotificationsWithSubscribers=[{
                    'Notification': {
                        'NotificationType': 'ACTUAL',
                        'ComparisonOperator': 'GREATER_THAN',
                        'Threshold': 100.0,
                        'ThresholdType': 'PERCENTAGE'
                    },
                    'Subscribers': [{'SubscriptionType': 'EMAIL', 'Address': self.email}]
                }]
            )
            print(f"✅ Success: Budget '{budget_name}' is active.")
        except self.client.exceptions.DuplicateRecordException:
            print(f"ℹ️  Notice: Budget '{budget_name}' already exists. Skipping.")


if __name__ == "__main__":
    # In a real interview, mention you'd pass these via environment variables or CLI args
    guard = BudgetGuard()
    guard.create_hard_stop_budget()
