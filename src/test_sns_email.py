import os
import boto3

AWS_REGION = "us-east-1"
SNS_TOPIC_ARN = os.environ.get("FINOPS_SNS_TOPIC_ARN", "")


def main():
    if not SNS_TOPIC_ARN:
        raise RuntimeError(
            "FINOPS_SNS_TOPIC_ARN is not set. "
            "Set it in Git Bash before running this test."
        )

    sns = boto3.client("sns", region_name=AWS_REGION)

    response = sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="AWS FinOps - Test Notification",
        Message=(
            "This is a test notification from your AI-Powered AWS FinOps "
            "Assistant. SNS email delivery is being tested. "
            "This is not a real cost alert."
        ),
    )

    print("Test notification submitted to Amazon SNS.")
    print("Message ID:", response["MessageId"])


if __name__ == "__main__":
    main()
