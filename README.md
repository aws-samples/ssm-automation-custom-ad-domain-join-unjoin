## Simplifying Active Directory domain join with AWS Systems Manager

# Overview
Deploy a custom AWS Systems Manager Automation runbook that automatically domain joins or unjoin from an [Active Directory (AD) domain](https://docs.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/active-directory-domain-services-overview). This runbook can be used with on-premises AD, self-managed AD running on [Amazon Elastic Compute Cloud (Amazon EC2) Windows instances](https://aws.amazon.com/windows/products/ec2/), or [AWS Managed Microsoft AD](https://aws.amazon.com/directoryservice/) and can be executed manually or automatically with services such as [Amazon EventBridge](https://aws.amazon.com/eventbridge/) or [AWS Lambda](https://aws.amazon.com/lambda/). The runbook leverages parameters stored in AWS Systems Manager Parameter Store. In particular, 4 parameters are created that include the AD domain name, AD domain username, AD domain user's password, and a specific Organizational Unit (OU) in AD.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

