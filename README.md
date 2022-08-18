## Simplifying Active Directory domain join with AWS Systems Manager

# Overview
Deploy a custom AWS Systems Manager Automation runbook that automatically domain joins or unjoins from an [Active Directory (AD) domain](https://docs.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/active-directory-domain-services-overview). This runbook can be used with on-premises AD, self-managed AD running on [Amazon Elastic Compute Cloud (Amazon EC2) Windows instances](https://aws.amazon.com/windows/products/ec2/), or [AWS Managed Microsoft AD](https://aws.amazon.com/directoryservice/) and can be executed manually or automatically with AWS services such as [AWS Systems Manager](https://aws.amazon.com/systems-manager/), [Amazon EventBridge](https://aws.amazon.com/eventbridge/), or [AWS Lambda](https://aws.amazon.com/lambda/). The runbook leverages 4 parameters stored in [Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html), to store the AD domain name, AD domain username, AD domain user's password, and a specific Organizational Unit (OU) in AD. The AD domain user's password is encrypted and decrypted with [AWS Key Management Service (AWS KMS)](https://aws.amazon.com/kms/) as a secure string.

## The Automation runbook workflow
There are 9 steps in total in the Automation workflow. Below are descriptions of the key steps and how they factor into the AD domain join/unjoin activities.
1. **assertInstanceIsWindows** - The runbook first checks if the EC2 instance is running Windows and will only continue if the platform is Windows.
2. **chooseDomainJoinActivity** - This is the crucial activity, where a user selects which activity they want to execute automatically: join an AD domain or unjoin from an AD domain.
   - Determined from the **DomainJoinActivity** parameter.
3. **joinDomain** & **unjoinDomain** - PowerShell to domain join or unjoin are  on the EC2 instances locally, respectively. A successful domain join will restart the instance, where a successful unjoin will stop the instance.
   - The tagging steps are **joinADEC2Tag** and **unjoinADEC2Tag**.
   - The PowerShell is wrapped in ```try``` and ```catch``` blocks. To learn more, visit [about_Try_Catch_Finally](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_try_catch_finally?view=powershell-7.2).
   - If either a domain join/unjoin fails, a **Failed** status is returned, the EC2 instance is tagged to reflect the failure (**failADEC2Tag**), and the EC2 instance is stopped.
   > The failures from the PowerShell are outputted and displayed in the Systems Manager Automation executions console. Users can troubleshoot the domain join/unjoin failures based on these common errors. Further enhancements can be made by additionally outputting the failures to [Amazon CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html) in custom [log groups created by Run Command](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-rc-setting-up-cwlogs.html). To learn more about log groups, visit the [AWS documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/Working-with-log-groups-and-streams.html).

# Deploy the Automation runbook and parameters
To deploy the runbook and parameters automatically, download and save the AWS CloudFormation template from Github, [**cfn-create-ssm-automation-parameters-adjoin.yml**](templates/cfn-create-ssm-automation-parameters-adjoin.yml), and save it locally to your computer to create a new CloudFormation stack. Creating a new stack will simplify the deployment of the Automation runbook and create the appropriate parameters to perform the AD join/unjoin activities automatically. To learn more about CloudFormation stack creation, visit the [AWS documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/GettingStarted.Walkthrough.html#GettingStarted.Walkthrough.createstack).

To create the Automation runbook manually, you can download the template separately from [here](templates/ssm-automation-domainjoinunjoin.yaml) and create a custom Automation runbook manually. Visit the AWS documentation to learn [how to create runbooks with the Document Builder](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-document-builder.html) or [how to create runbooks with the Editor](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-document-editor.html).

# Parameter Store
The Automation runbook requires parameters stored in Systems Manager Parameter Store to complete the domain join and unjoining activities. If you chose to deploy the environment using the CloudFormation stack, these parameters are created automatically. Otherwise, the parameters must be created manually. This includes the AD domain name (FQDN), AD username, AD password, and a targetOU. To learn more about Parameter Store, visit the [AWS documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html).

Below are details of the parameters that are created by the CloudFormation stack or manually if you choose not to use CloudFormation (NOTE: the parameter names and values are cAsE-SeNsItIvE).

|Name (do not change these values)	|Type	|Data type	|Value (example values)	|AWS KMS Key ID Required	|
|---	|---	|---	|---	|---	|
|domainName	|String	|text	|corp.example.com	|No	|
|domainJoinUserName	|String	|text	|CORP\Admin	|No	|
|domainJoinPassword	|SecureString	|text	|YOURPASSWORD	|Yes	|
|defaultTargetOU	|String	|text	|**OU=Computers,OU=CORP,dc=corp,dc=example,dc=com**	|No	|

## PowerShell

Within the Systems Manager Automation runbook there are two steps where either domain join or domain unjoin activities are executed. These steps call a [Systems Manage Command document (SSM Document)](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssm-docs.html) to execute this code. Specifically, the SSM Command document that is executed is **AWS-RunPowerShellScript**, which simply executes any code that is passed as an input parameter. Below are the PowerShell code blocks used to perform domain join and domain unjoin activities, respectively.

### Domain join
```powershell
If ((Get-CimInstance -ClassName 'Win32_ComputerSystem' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty 'PartOfDomain') -eq $false) {
    Try {
        $targetOU = (Get-SSMParameterValue -Name 'defaultTargetOU' -ErrorAction Stop).Parameters[0].Value
        $domainName = (Get-SSMParameterValue -Name 'domainName' -ErrorAction Stop).Parameters[0].Value
        $domainJoinUserName = (Get-SSMParameterValue -Name 'domainJoinUserName' -ErrorAction Stop).Parameters[0].Value
        $domainJoinPassword = (Get-SSMParameterValue -Name 'domainJoinPassword' -WithDecryption:$true -ErrorAction Stop).Parameters[0].Value | ConvertTo-SecureString -AsPlainText -Force
    } Catch [System.Exception] {
        Write-Output " Failed to get SSM Parameter(s) $_"
    }
    $domainCredential = New-Object System.Management.Automation.PSCredential($domainJoinUserName, $domainJoinPassword)

    Try {
        Write-Output "Attempting to join $env:COMPUTERNAME to Active Directory domain: $domainName and moving $env:COMPUTERNAME to the following OU: $targetOU."
        Add-Computer -ComputerName $env:COMPUTERNAME -DomainName $domainName -Credential $domainCredential -OUPath $targetOU -Restart:$false -ErrorAction Stop 
    } Catch [System.Exception] {
        Write-Output "Failed to add computer to the domain $_"
        Exit 1
    }
} Else {
    Write-Output "$env:COMPUTERNAME is already part of the Active Directory domain $domainName."
    Exit 0
}
```

### Domain unjoin
```powershell
If ((Get-CimInstance -ClassName 'Win32_ComputerSystem' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty 'PartOfDomain') -eq $true) {
    Try {
        $domainName = (Get-SSMParameterValue -Name 'domainName' -ErrorAction Stop).Parameters[0].Value
        $domainJoinUserName = (Get-SSMParameterValue -Name 'domainJoinUserName' -ErrorAction Stop).Parameters[0].Value
        $domainJoinPassword = (Get-SSMParameterValue -Name 'domainJoinPassword' -WithDecryption:$true -ErrorAction Stop).Parameters[0].Value | ConvertTo-SecureString -AsPlainText -Force
    } Catch [System.Exception] {
        Write-Output "Failed to get SSM Parameter(s) $_"
    }

    $domainCredential = New-Object System.Management.Automation.PSCredential($domainJoinUserName, $domainJoinPassword)

    If (-not (Get-WindowsFeature -Name 'RSAT-AD-Tools' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty 'Installed')) {
        Write-Output 'Installing RSAT AD Tools to allow domain joining'
        Try {
            $Null = Add-WindowsFeature -Name 'RSAT-AD-Tools' -ErrorAction Stop
        } Catch [System.Exception] {
            Write-Output "Failed to install RSAT AD Tools $_"
            Exit 1
        }    
    }
    
    $getADComputer = (Get-ADComputer -Identity $env:COMPUTERNAME -Credential $domainCredential)
    $distinguishedName = $getADComputer.DistinguishedName

    Try {
        Remove-Computer -ComputerName $env:COMPUTERNAME -UnjoinDomainCredential $domainCredential -Verbose -Force -Restart:$false -ErrorAction Stop
        Remove-ADComputer -Credential $domainCredential -Identity $distinguishedName -Server $domainName -Confirm:$False -Verbose -ErrorAction Stop
    } Catch [System.Exception] {
        Write-Output "Failed to remove $env:COMPUTERNAME from the $domainName domain and in a Windows Workgroup. $_"
        Exit 1
    }  
} Else {
    Write-Output "$env:COMPUTERNAME is not part of the Active Directory domain $domainName and already part of a Windows Workgroup."
    Exit 0
}
```

With the exception of the parameters from the Systems Manager Parameter Store, the PowerShell script should be familiar to any admin who leverages PowerShell AD cmdlets to execute domain join activities. There are **exit codes** specific to Systems Manager that allow the Automation runbook to identify failures during the domain join or unjoin process. Without the exit codes, a failed domain join, for example, may still be marked as **Success** despite not having been added to an AD domain. Learn more about exit codes by visiting [AWS documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/command-exit-codes.html).

NOTE: the PowerShell can be customized as needed. Also, AD credentials are currently stored as parameters in Systems Manager Parameter Store. However, customers can choose to store these credentials as secrets in AWS Secrets Manager. To learn more about Secrest Manager, visit the [AWS documentation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
