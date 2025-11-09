"""
Pydantic AI Agent with Mem0, Langfuse, and Guardrails AI

Main application entry point.
"""
import asyncio
from typing import Optional
import httpx
import re
from datetime import datetime
import pytz
try:
    import ntplib
except ImportError:
    ntplib = None  # NTP sync will be disabled if ntplib not available

from pydantic_ai import Agent
try:
    from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
except ImportError:
    from pydantic_ai.models.openai import OpenAIModel

# Mem0 for long-term memory
from mem0 import Memory
from hybrid_memory import HybridMemoryManager

# Langfuse for observability
from langfuse import Langfuse
try:
    from langfuse.decorators import observe
except ImportError:
    # Langfuse 3.x compatibility
    from langfuse import observe

# Guardrails AI - disabled for now
# from guardrails import Guard
# try:
#     from guardrails.hub import ToxicLanguage
# except ImportError:
#     ToxicLanguage = None  # Guardrails validator not available

# Local imports
from config import config
from prompts import get_system_prompt
from utils import (
    setup_logging,
    print_welcome_message,
    print_user_message,
    print_agent_message,
    print_system_message,
    print_error,
    sanitize_input,
    is_exit_command,
    create_conversation_metadata,
)

# Setup logging
logger = setup_logging(config.LOG_LEVEL)

# Custom fact extraction prompt for Mem0
# Note: This works best with larger models (8B+). With smaller models like llama3.2 (3B),
# some facts from assistant messages may be incorrectly extracted.
CUSTOM_FACT_EXTRACTION_PROMPT = """CRITICAL: You MUST return ONLY this exact JSON structure. NO other formats allowed:
{"facts": ["fact1", "fact2", ...]}

Extract facts from the user message. Each fact should be a separate string in the "facts" array.

RULES:
1. ALWAYS include the "facts" key - even if empty: {"facts": []}
2. Extract location details with full specificity (city, neighborhood, area)
3. Break down compound statements into separate facts
4. Extract personal info, preferences, actions, tools, dates, times
5. User questions return empty array: {"facts": []}

MANDATORY OUTPUT FORMAT - MUST USE THIS EXACT STRUCTURE:
{"facts": ["string1", "string2", ...]}

NO OTHER JSON STRUCTURES ARE ALLOWED. The response MUST have a "facts" key with an array value.

Examples:

user: My name is John
assistant: Hi John!
{"facts": ["Name is John"]}

user: I work at Tesla as an engineer
assistant: Tesla is great!
{"facts": ["Works at Tesla", "Works as engineer"]}

user: I'm travelling to Paris next week
assistant: Paris is beautiful!
{"facts": ["Travelling to Paris", "Leaving next week"]}

user: I live on the north side of Indianapolis
assistant: That's a nice area!
{"facts": ["Lives in Indianapolis", "Lives on north side of Indianapolis"]}

user: I live in San Francisco, specifically in the Mission District
assistant: The Mission is vibrant!
{"facts": ["Lives in San Francisco", "Lives in Mission District"]}

user: I usually work from my office downtown near 5th and Main
assistant: That's convenient!
{"facts": ["Works from office", "Office is downtown", "Office near 5th and Main"]}

user: Where am I going?
assistant: You're going to Spain.
{"facts": []}

user: I'm a data scientist
assistant: Data science is interesting!
{"facts": ["Works as data scientist"]}

user: My order #12345 hasn't arrived yet.
assistant: I'm sorry for your inconvenience.
{"facts": ["Order #12345 not received"]}

user: I'm John Doe, and I'd like to return the shoes I bought last week.
assistant: No problem, I'll help you with that.
{"facts": ["Customer name: John Doe", "Wants to return shoes", "Purchase made last week"]}

user: I ordered a red shirt, size medium, but received a blue one instead.
assistant: I'm sorry about that. Let me check with the warehouse.
{"facts": ["Ordered red shirt, size medium", "Received blue shirt instead"]}

user: I prefer working in the mornings
assistant: Morning work is productive!
{"facts": ["Prefers working in mornings"]}

user: I used the GitHub API to search for Python repositories
assistant: I found 150 results.
{"facts": ["Used GitHub API", "Searched for Python repositories", "Action: API search"]}

user: I deployed my app to Azure using Docker containers
assistant: Deployment successful!
{"facts": ["Deployed app to Azure", "Used Docker containers", "Deployment method: Docker", "Platform: Azure"]}

user: I ran a PowerShell script to clean up stale AD accounts
assistant: The script completed successfully.
{"facts": ["Ran PowerShell script", "Script purpose: clean up stale AD accounts", "Tool: PowerShell", "Target: Active Directory"]}

user: I created a new Intune policy for our marketing team's devices
assistant: Policy created.
{"facts": ["Created Intune policy", "Policy target: marketing team devices", "Tool: Microsoft Intune"]}

user: I queried the database using SQL to get customer sales data from Q3
assistant: Here are the results.
{"facts": ["Queried database", "Query language: SQL", "Data retrieved: customer sales", "Time period: Q3"]}

user: I automated the backup process with a cron job running every night at 2am
assistant: Automation set up successfully.
{"facts": ["Automated backup process", "Method: cron job", "Schedule: every night at 2am", "Action type: automation"]}

user: I used Postman to test the REST API endpoints for authentication
assistant: All tests passed.
{"facts": ["Used Postman", "Tested REST API endpoints", "Endpoints tested: authentication", "Action: API testing"]}

user: I wrote a Python script using pandas to analyze CSV files
assistant: Great approach!
{"facts": ["Wrote Python script", "Used pandas library", "Script purpose: analyze CSV files", "Programming language: Python"]}

user: I configured Cloudflare tunnels for secure remote access
assistant: Tunnels are now active.
{"facts": ["Configured Cloudflare tunnels", "Purpose: secure remote access", "Tool: Cloudflare"]}

user: I used CrowdStrike Falcon to scan for malware across all endpoints
assistant: Scan completed.
{"facts": ["Used CrowdStrike Falcon", "Action: malware scan", "Scan scope: all endpoints", "Security tool: CrowdStrike Falcon"]}

user: I created an Azure Logic App to sync data between SharePoint and SQL
assistant: Logic App deployed.
{"facts": ["Created Azure Logic App", "Integration: SharePoint to SQL", "Tool: Azure Logic Apps", "Data source: SharePoint", "Data destination: SQL"]}

user: I prefer using kubectl for Kubernetes management
assistant: That's a solid choice!
{"facts": ["Prefers kubectl", "Tool used for: Kubernetes management", "Preferred tool: kubectl"]}

user: I troubleshot the issue using the Microsoft Graph API explorer
assistant: Good debugging approach.
{"facts": ["Troubleshot using Microsoft Graph API explorer", "Tool: Microsoft Graph API", "Action: debugging/troubleshooting"]}

user: I ran an N-Central automation policy to update agents across all client sites
assistant: Policy executed successfully.
{"facts": ["Ran N-Central automation policy", "Action: update agents", "Scope: all client sites", "Tool: N-Central RMM"]}

user: I used the Microsoft Graph API to query stale Intune devices for Acme Corp
assistant: Found 23 stale devices.
{"facts": ["Used Microsoft Graph API", "Queried Intune devices", "Client: Acme Corp", "Device status: stale", "Tool: Microsoft Graph", "Target: Intune"]}

user: I deployed an Azure Function with Python to automate Office 365 license reporting
assistant: Function is live.
{"facts": ["Deployed Azure Function", "Function language: Python", "Purpose: Office 365 license reporting", "Platform: Azure Functions", "Automation target: Office 365 licenses"]}

user: I created a PowerShell script to cross-reference AD, Entra ID, and CrowdStrike data
assistant: Script working well.
{"facts": ["Created PowerShell script", "Script integrates: AD, Entra ID, CrowdStrike", "Purpose: cross-reference data", "Tool: PowerShell", "Platforms: Active Directory, Entra ID, CrowdStrike"]}

user: I configured FSLogix App Masking for the kiosk environment at Smith Industries
assistant: Configuration applied.
{"facts": ["Configured FSLogix App Masking", "Client: Smith Industries", "Environment: kiosk", "Tool: FSLogix", "Use case: application control"]}

user: I built a Chocolatey package for deploying our standard software stack
assistant: Package ready for deployment.
{"facts": ["Built Chocolatey package", "Purpose: deploy software stack", "Package type: standard software", "Tool: Chocolatey"]}

user: I'm troubleshooting Azure AD Connect sync issues between on-prem AD and Entra ID
assistant: Let me help with that.
{"facts": ["Troubleshooting Azure AD Connect", "Issue: sync problems", "Source: on-premises AD", "Destination: Entra ID", "Tool: Azure AD Connect"]}

user: I used N-Central's API to pull device inventory for all managed endpoints
assistant: Inventory retrieved.
{"facts": ["Used N-Central API", "Action: pull device inventory", "Scope: all managed endpoints", "Tool: N-Central RMM", "Data type: device inventory"]}

user: I set up an Intune dynamic group for Windows 11 devices in the finance department
assistant: Dynamic group created.
{"facts": ["Set up Intune dynamic group", "Device OS: Windows 11", "Department: finance", "Tool: Microsoft Intune", "Group type: dynamic"]}

user: I deployed Azure Container Apps for hosting our client portal microservices
assistant: Container Apps running.
{"facts": ["Deployed Azure Container Apps", "Purpose: client portal hosting", "Architecture: microservices", "Platform: Azure Container Apps"]}

user: I wrote a Logic App to handle Microsoft Graph API throttling for bulk operations
assistant: Logic App is handling throttling well.
{"facts": ["Created Logic App", "Purpose: handle API throttling", "API: Microsoft Graph", "Use case: bulk operations", "Tool: Azure Logic Apps"]}

user: I configured hybrid Azure AD join for workstations at three different client locations
assistant: Hybrid join configured.
{"facts": ["Configured hybrid Azure AD join", "Device type: workstations", "Number of locations: 3", "Join type: hybrid Azure AD", "Tool: Azure AD"]}

user: I'm using CrowdStrike Falcon's RTR to remotely remediate the infected machine
assistant: Remediation in progress.
{"facts": ["Using CrowdStrike Falcon RTR", "Action: remote remediation", "Target: infected machine", "Tool: CrowdStrike Falcon", "Feature: Real Time Response"]}

user: I deployed FSLogix profile containers to Azure Files for the VDI environment
assistant: Profiles are syncing.
{"facts": ["Deployed FSLogix profile containers", "Storage: Azure Files", "Environment: VDI", "Tool: FSLogix", "Storage platform: Azure Files"]}

user: I'm using the Exchange Online PowerShell module to manage mailbox permissions
assistant: What changes do you need to make?
{"facts": ["Using Exchange Online PowerShell module", "Purpose: manage mailbox permissions", "Platform: Exchange Online", "Tool: PowerShell"]}

user: I created a conditional access policy in Entra ID requiring MFA for admin accounts
assistant: Policy is active.
{"facts": ["Created conditional access policy", "Platform: Entra ID", "Requirement: MFA", "Target: admin accounts", "Security control: multi-factor authentication"]}

user: I set up Azure Blob Storage lifecycle policies to archive old backup files after 90 days
assistant: Lifecycle policy configured.
{"facts": ["Set up Azure Blob Storage lifecycle policy", "Action: archive files", "Trigger: after 90 days", "File type: old backups", "Platform: Azure Blob Storage"]}

user: I prefer using the Az PowerShell module over Azure CLI for automation scripts
assistant: Both are good tools.
{"facts": ["Prefers Az PowerShell module", "Preference over: Azure CLI", "Use case: automation scripts", "Tool: Azure PowerShell"]}

user: I ran a compliance scan in N-Central across all Windows servers for missing patches
assistant: Scan complete.
{"facts": ["Ran compliance scan", "Tool: N-Central", "Target: Windows servers", "Scope: all servers", "Scan purpose: missing patches"]}

user: I used Microsoft Defender API to query threat detections for the last 30 days
assistant: Here are the results.
{"facts": ["Used Microsoft Defender API", "Action: query threat detections", "Time period: last 30 days", "Tool: Microsoft Defender", "Data type: threat detections"]}

user: I'm deploying Intune Win32 apps using intunewin packages for silent installation
assistant: Deployment configured.
{"facts": ["Deploying Intune Win32 apps", "Package format: intunewin", "Installation type: silent", "Tool: Microsoft Intune", "App deployment method: Win32"]}

user: I built a SharePoint site for client documentation using modern templates
assistant: Site looks good!
{"facts": ["Built SharePoint site", "Purpose: client documentation", "Template type: modern", "Platform: SharePoint"]}

user: I configured Azure Automation runbooks to start/stop VMs on a schedule
assistant: Runbooks are scheduled.
{"facts": ["Configured Azure Automation runbooks", "Action: start/stop VMs", "Trigger: scheduled", "Platform: Azure Automation", "Resource type: virtual machines"]}

user: I'm using Microsoft Endpoint Manager to manage both Intune and ConfigMgr from one console
assistant: That's the unified approach.
{"facts": ["Using Microsoft Endpoint Manager", "Manages: Intune and ConfigMgr", "Interface: unified console", "Tool: Microsoft Endpoint Manager"]}

user: I troubleshot wireless connectivity on Dell Latitude laptops by updating Intel drivers
assistant: Did that resolve it?
{"facts": ["Troubleshot wireless connectivity", "Device: Dell Latitude laptops", "Solution: updated Intel drivers", "Driver type: Intel wireless", "Issue: connectivity problems"]}

user: I set up Azure VPN Gateway for site-to-site connectivity to client's on-prem network
assistant: VPN tunnel is up.
{"facts": ["Set up Azure VPN Gateway", "Connection type: site-to-site", "Destination: client on-premises network", "Tool: Azure VPN Gateway"]}

user: I use PrtgScr for capturing screenshots when documenting client issues
assistant: Good documentation practice.
{"facts": ["Uses PrtgScr", "Purpose: capture screenshots", "Use case: document client issues", "Tool: Print Screen"]}

user: I created a Microsoft 365 group with Teams integration for project collaboration
assistant: Group is ready.
{"facts": ["Created Microsoft 365 group", "Integration: Microsoft Teams", "Purpose: project collaboration", "Platform: Microsoft 365"]}

user: I ran Get-ADComputer in PowerShell to audit stale computer accounts older than 90 days
assistant: How many did you find?
{"facts": ["Ran Get-ADComputer cmdlet", "Tool: PowerShell", "Purpose: audit stale accounts", "Criteria: older than 90 days", "Target: computer accounts", "Platform: Active Directory"]}

user: I'm using Azure Monitor to track Logic App execution failures and performance metrics
assistant: Good visibility setup.
{"facts": ["Using Azure Monitor", "Monitoring: Logic App executions", "Metrics tracked: failures and performance", "Tool: Azure Monitor", "Target: Logic Apps"]}

user: I scheduled the Azure AD Connect sync to run every 30 minutes
assistant: Sync schedule configured.
{"facts": ["Scheduled Azure AD Connect sync", "Frequency: every 30 minutes", "Tool: Azure AD Connect", "Action type: scheduled sync"]}

user: The client's Office 365 E3 licenses expire on December 15, 2025
assistant: I'll add a reminder.
{"facts": ["Client has Office 365 E3 licenses", "License expiration date: December 15, 2025", "License type: Office 365 E3"]}

user: I set up a maintenance window every Tuesday from 2am to 4am for server patching
assistant: Maintenance window created.
{"facts": ["Set up maintenance window", "Day: every Tuesday", "Time: 2am to 4am", "Duration: 2 hours", "Purpose: server patching", "Recurrence: weekly"]}

user: Yesterday I migrated 50 mailboxes from on-prem Exchange to Exchange Online
assistant: That's solid progress.
{"facts": ["Migrated mailboxes", "Migration date: yesterday", "Quantity: 50 mailboxes", "Source: on-premises Exchange", "Destination: Exchange Online"]}

user: The backup job runs daily at 11pm and takes approximately 3 hours to complete
assistant: Good to know the timing.
{"facts": ["Backup job runs daily", "Start time: 11pm", "Duration: approximately 3 hours", "Frequency: daily", "Estimated completion: 2am"]}

user: I noticed the issue started last Thursday around 3pm
assistant: That helps narrow it down.
{"facts": ["Issue start date: last Thursday", "Issue start time: around 3pm", "Status: problem identified"]}

user: The certificate expires in 45 days and needs renewal by January 20, 2026
assistant: Better schedule that renewal.
{"facts": ["Certificate expires in 45 days", "Renewal deadline: January 20, 2026", "Action needed: certificate renewal"]}

user: I schedule all client patching for the second Saturday of each month between midnight and 6am
assistant: Consistent schedule.
{"facts": ["Patching schedule: second Saturday of each month", "Time window: midnight to 6am", "Duration: 6 hours", "Target: all clients", "Recurrence: monthly"]}

user: The domain controller was last rebooted 127 days ago on July 1, 2025
assistant: That's a long uptime.
{"facts": ["Domain controller last reboot: 127 days ago", "Last reboot date: July 1, 2025", "Device type: domain controller", "Uptime: 127 days"]}

user: I configured the Azure Function to run every 15 minutes during business hours
assistant: Function schedule set.
{"facts": ["Configured Azure Function", "Frequency: every 15 minutes", "Active period: business hours only", "Platform: Azure Functions"]}

user: The script has been running in production for 6 months without issues
assistant: Good stability.
{"facts": ["Script in production for 6 months", "Status: no issues", "Stability period: 6 months"]}

user: I upgraded all workstations from Windows 10 to Windows 11 over a 3-week period in August
assistant: Nice migration timeline.
{"facts": ["Upgraded workstations", "Source OS: Windows 10", "Target OS: Windows 11", "Duration: 3 weeks", "Migration month: August", "Device type: all workstations"]}

user: The warranty on the Dell servers expires Q2 2026
assistant: Note that for planning.
{"facts": ["Dell servers warranty expires Q2 2026", "Device type: Dell servers", "Warranty period end: Q2 2026"]}

user: I created a recurring report that emails every Monday at 8am with the previous week's metrics
assistant: Report scheduled.
{"facts": ["Created recurring report", "Frequency: every Monday", "Send time: 8am", "Content: previous week's metrics", "Delivery method: email", "Recurrence: weekly"]}

user: The migration is planned for November 22-24, 2025 over the Thanksgiving weekend
assistant: Good timing for minimal disruption.
{"facts": ["Migration planned for November 22-24, 2025", "Duration: 3 days", "Timing: Thanksgiving weekend", "Action: migration"]}

user: I deployed the new firewall rules at 10:30pm last night with no reported issues
assistant: Smooth deployment.
{"facts": ["Deployed firewall rules", "Deployment time: 10:30pm last night", "Status: no issues reported", "Action: firewall rule deployment"]}

user: The SQL backup retention policy keeps daily backups for 30 days and monthly backups for 1 year
assistant: Good retention strategy.
{"facts": ["SQL backup retention policy configured", "Daily backups retained: 30 days", "Monthly backups retained: 1 year", "Database type: SQL"]}

user: I changed their password reset frequency from 90 days to 180 days last month
assistant: Policy updated.
{"facts": ["Changed password reset frequency", "Old frequency: 90 days", "New frequency: 180 days", "Change made: last month", "Policy type: password reset"]}

user: The system went offline at 2:47am and was restored by 3:15am
assistant: Quick recovery.
{"facts": ["System went offline at 2:47am", "System restored at 3:15am", "Downtime duration: 28 minutes", "Status: restored"]}

user: We do quarterly security audits in January, April, July, and October
assistant: Good audit cadence.
{"facts": ["Security audits conducted quarterly", "Audit months: January, April, July, October", "Frequency: quarterly", "Audit type: security"]}

user: The printer firmware was last updated 8 months ago
assistant: Might be time for an update.
{"facts": ["Printer firmware last updated 8 months ago", "Device type: printer", "Update type: firmware", "Time since update: 8 months"]}

user: I scheduled a test failover for December 10th at 6pm to verify DR procedures
assistant: Test scheduled.
{"facts": ["Scheduled test failover", "Date: December 10th", "Time: 6pm", "Purpose: verify DR procedures", "Test type: failover"]}

user: The MFA rollout took 4 weeks and was completed September 30, 2025
assistant: Project completed.
{"facts": ["MFA rollout duration: 4 weeks", "Completion date: September 30, 2025", "Project: MFA rollout", "Status: completed"]}

user: I check the N-Central dashboard every morning at 9am for alerts
assistant: Good monitoring routine.
{"facts": ["Checks N-Central dashboard", "Frequency: every morning", "Time: 9am", "Purpose: check for alerts", "Tool: N-Central", "Routine: daily"]}

user: The tenant was created on March 15, 2024 and migrated to our management on June 1, 2025
assistant: Got the timeline.
{"facts": ["Tenant created: March 15, 2024", "Tenant migration date: June 1, 2025", "Time between creation and migration: approximately 2.5 months", "Status: under our management"]}

user: Their support contract renews annually every April 1st for $12,000
assistant: Contract noted.
{"facts": ["Support contract renews annually", "Renewal date: April 1st", "Contract value: $12,000", "Renewal frequency: annual"]}

user: I run the stale account cleanup script bi-weekly on alternating Fridays
assistant: Regular maintenance schedule.
{"facts": ["Script: stale account cleanup", "Frequency: bi-weekly", "Day: alternating Fridays", "Script purpose: cleanup stale accounts"]}

user: The SLA guarantees 99.9% uptime which allows for about 8.76 hours of downtime per year
assistant: That's the calculation.
{"facts": ["SLA uptime guarantee: 99.9%", "Allowed downtime: 8.76 hours per year", "Agreement type: SLA"]}

user: Peak usage hours are between 9am-11am and 2pm-4pm on weekdays
assistant: Good to know for planning.
{"facts": ["Peak usage: 9am-11am weekdays", "Peak usage: 2pm-4pm weekdays", "Days: weekdays only"]}

user: I started the migration at midnight and it's been running for 6 hours so far
assistant: Migration in progress.
{"facts": ["Migration start time: midnight", "Current duration: 6 hours", "Status: in progress", "Current time estimate: 6am"]}

user: The incident occurred at exactly 4:23pm EST on November 1st, 2025
assistant: Timestamp recorded.
{"facts": ["Incident time: 4:23pm EST", "Incident date: November 1st, 2025", "Timezone: EST", "Event: incident"]}

user: I'm scheduling routine reboots for all servers on the first Sunday of each month at 3am
assistant: Reboot schedule configured.
{"facts": ["Routine reboots scheduled", "Frequency: first Sunday of each month", "Time: 3am", "Target: all servers", "Recurrence: monthly"]}

user: Their Microsoft 365 tenant has been active for 18 months since May 2024
assistant: Tenant age noted.
{"facts": ["Microsoft 365 tenant active for 18 months", "Tenant start date: May 2024", "Platform: Microsoft 365"]}

user: I'm reading Atomic Habits and trying to build a morning workout routine
assistant: Great book and goal!
{"facts": ["Reading Atomic Habits", "Book: Atomic Habits", "Building morning workout routine", "Routine: morning workout"]}

user: My daughter Sarah is taking piano lessons at Harmony Music School every Wednesday
assistant: That's wonderful!
{"facts": ["Has daughter named Sarah", "Sarah takes piano lessons", "School: Harmony Music School", "Lesson schedule: every Wednesday"]}

user: I'm allergic to shellfish and prefer vegan restaurants
assistant: I'll remember your dietary needs.
{"facts": ["Allergic to shellfish", "Prefers vegan restaurants", "Dietary restriction: shellfish"]}

user: My dentist Dr. Miller is at 123 Oak Street and I see him every 6 months
assistant: Regular dental care is important.
{"facts": ["Dentist: Dr. Miller", "Dentist location: 123 Oak Street", "Visit frequency: every 6 months", "Healthcare provider: Dr. Miller"]}

user: I have a Netflix subscription that costs $15.99 per month and renews on the 5th
assistant: Subscription noted.
{"facts": ["Has Netflix subscription", "Netflix cost: $15.99 per month", "Renewal date: 5th of each month", "Subscription: Netflix"]}

user: I'm learning Spanish using Duolingo for my trip to Barcelona next summer
assistant: Barcelona will be amazing!
{"facts": ["Learning Spanish", "Tool: Duolingo", "Traveling to Barcelona", "Trip timing: next summer", "Learning purpose: Barcelona trip"]}

user: I ordered a standing desk from Amazon for $450, order #12345, arriving Friday
assistant: Great purchase!
{"facts": ["Ordered standing desk", "Vendor: Amazon", "Cost: $450", "Order number: 12345", "Arrival date: Friday"]}

user: My goal is to run a marathon by December, currently training 4 days a week
assistant: That's an ambitious goal!
{"facts": ["Goal: run a marathon", "Target date: December", "Training frequency: 4 days a week", "Currently training for marathon"]}

user: I watch The Office every night before bed, it helps me relax
assistant: Classic show!
{"facts": ["Watches The Office", "Viewing time: every night before bed", "Purpose: helps relaxation", "Show: The Office", "Evening routine: watch TV"]}

user: I take my medication Lipitor 20mg every morning with breakfast
assistant: Consistent medication schedule is good.
{"facts": ["Takes Lipitor 20mg", "Dosage: 20mg", "Schedule: every morning with breakfast", "Medication: Lipitor"]}

user: My brother Mark lives in Seattle and works as a software engineer at Microsoft
assistant: Cool!
{"facts": ["Has brother named Mark", "Mark lives in Seattle", "Mark works as software engineer", "Mark works at Microsoft"]}

user: I play tennis twice a week at Riverside Courts with my friend Tom
assistant: Sounds fun!
{"facts": ["Plays tennis", "Tennis frequency: twice a week", "Location: Riverside Courts", "Plays with Tom", "Friend: Tom"]}

user: I'm training for a 5K in March and running 3 miles every other day
assistant: Keep up the training!
{"facts": ["Training for 5K race", "Race date: March", "Training: running 3 miles", "Frequency: every other day"]}

user: My anniversary is June 12th and I've been married for 15 years
assistant: Congratulations!
{"facts": ["Anniversary date: June 12th", "Married for 15 years", "Relationship status: married"]}

user: I have a gym membership at LA Fitness that costs $40 per month
assistant: Good to stay active!
{"facts": ["Has gym membership", "Gym: LA Fitness", "Membership cost: $40 per month", "Subscription: LA Fitness"]}

user: My favorite restaurant is Luigi's on Main Street, I go there monthly
assistant: Italian food is great!
{"facts": ["Favorite restaurant: Luigi's", "Restaurant location: Main Street", "Visit frequency: monthly"]}

user: I'm studying for the AWS Solutions Architect certification exam in December
assistant: Good luck with your studies!
{"facts": ["Studying for AWS Solutions Architect certification", "Exam date: December", "Certification: AWS Solutions Architect"]}

user: I have a standing meeting with my team every Monday at 10am
assistant: Regular team sync.
{"facts": ["Has standing team meeting", "Meeting day: every Monday", "Meeting time: 10am", "Meeting type: team meeting"]}

user: My son plays soccer and has practice on Tuesdays and Thursdays at 5pm
assistant: Youth sports are great!
{"facts": ["Has son who plays soccer", "Soccer practice days: Tuesdays and Thursdays", "Practice time: 5pm"]}

user: I'm vegetarian and have been for 5 years
assistant: Plant-based lifestyle!
{"facts": ["Is vegetarian", "Vegetarian for 5 years", "Dietary preference: vegetarian"]}

user: I'm learning to play guitar and practice 30 minutes every evening
assistant: Music is rewarding!
{"facts": ["Learning guitar", "Practice duration: 30 minutes", "Practice frequency: every evening", "Instrument: guitar"]}

user: My car insurance with State Farm renews annually in September for $1,200
assistant: Annual renewal noted.
{"facts": ["Car insurance provider: State Farm", "Renewal frequency: annually", "Renewal month: September", "Insurance cost: $1,200 per year"]}

user: I volunteer at the animal shelter on Saturday mornings
assistant: That's wonderful volunteer work!
{"facts": ["Volunteers at animal shelter", "Volunteer day: Saturday mornings", "Activity: animal shelter volunteering"]}

user: My favorite podcast is The Daily and I listen to it during my morning commute
assistant: Good listening!
{"facts": ["Favorite podcast: The Daily", "Listens during morning commute", "Podcast: The Daily"]}

user: I'm trying to drink 8 glasses of water a day as a health goal
assistant: Hydration is important!
{"facts": ["Health goal: drink 8 glasses of water daily", "Target: 8 glasses per day", "Goal type: hydration"]}

user: My daughter's birthday is October 15th and she's turning 8
assistant: Plan something fun!
{"facts": ["Daughter's birthday: October 15th", "Daughter turning 8 years old", "Age: 8"]}

Return: {"facts": [...]}
"""

CUSTOM_ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting entities and their relationships from conversations about IT infrastructure, MSP operations, technical workflows, and personal contexts.

CRITICAL EXTRACTION RULES:
1. **Extract ONLY from USER messages** - DO NOT extract entities or relationships from assistant/agent responses
2. **Use conversation context** - If a user mentions "town" or "city" without naming it, look at previous context (company location, etc.) to infer which city
3. **Create hierarchical location relationships** - When extracting neighborhoods/areas (like "north side of town"), ALWAYS link them to the parent city using PART_OF relationship
4. **Ignore agent responses** - Messages like "I don't have that information" should be completely ignored for extraction

Extract ONLY concrete entities and their relationships. Break down compound information into separate entities and relationships.

ENTITY TYPES:

**Professional/Technical:**
- Person: Names of individuals
- Organization/Client: Company names, client names
- Tool/Platform: Software, APIs, services, applications (Azure, Intune, N-Central, CrowdStrike, etc.)
- Project: Specific projects or initiatives
- Device: Computers, servers, endpoints with names/identifiers
- Environment: Kiosk, VDI, production, test environments
- Team/Department: Groups within organizations
- Technology: Programming languages, protocols, frameworks
- Skill/Expertise: Technical abilities or knowledge areas
- Action/Task: Specific operations, automations, scripts
- Issue/Incident: Problems, errors, tickets
- Policy/Configuration: Rules, settings, configurations
- Resource: Azure resources, storage, networks, infrastructure components

**Location & Geography:**
- Location: Places with full specificity (city, neighborhood, area, office location)
- Address: Specific street addresses
- Venue: Restaurants, stores, facilities

**Temporal:**
- Temporal: Dates, schedules, time windows, deadlines, frequencies
- Event: Meetings, appointments, celebrations, milestones

**Personal & Lifestyle:**
- Hobby/Interest: Activities, pastimes, interests
- Media: Books, movies, TV shows, podcasts, music, games
- Food: Dishes, restaurants, cuisines, dietary restrictions
- Health: Medical conditions, medications, doctors, fitness activities
- Relationship: Family members, friends, contacts (with context)

**Financial & Commerce:**
- Account: Bank accounts, investment accounts, subscriptions
- Product: Physical products, purchases
- Service: Subscription services, memberships
- Transaction: Orders, purchases, payments

**Education & Learning:**
- Course: Classes, training programs
- Certification: Professional certifications, qualifications
- Institution: Schools, universities, training centers

**Documents & Content:**
- Document: Files, reports, contracts, notes
- Website: URLs, online resources
- Communication: Email threads, messages, channels

**Goals & Objectives:**
- Goal: Personal or professional objectives
- Habit: Regular routines, practices
- Preference: Likes, dislikes, choices

RELATIONSHIP TYPES:

**Professional:**
- WORKS_AT, WORKS_AS, MANAGES, LEADS, REPORTS_TO
- USES_TOOL, PREFERS_TOOL, DEPLOYED, CONFIGURED
- MANAGES_CLIENT, HAS_ENVIRONMENT
- CREATED, BUILT, DEVELOPED, WROTE
- INTEGRATES_WITH, CONNECTS_TO, SYNCS_WITH
- TARGETS, APPLIED_TO, OPERATES_ON
- RESOLVED_WITH, FIXED_BY, CAUSED_BY
- MEMBER_OF, PART_OF, BELONGS_TO

**Location & Movement:**
- LIVES_IN, WORKS_FROM, LOCATED_IN, LOCATED_AT
- TRAVELS_TO, VISITED, MOVING_TO

**Temporal:**
- SCHEDULED_FOR, EXPIRES_ON, DUE_ON, RUNS_AT
- STARTED_ON, COMPLETED_ON, OCCURRED_ON
- HAPPENS_EVERY, REPEATS_ON

**Personal:**
- INTERESTED_IN, ENJOYS, DISLIKES
- PRACTICES, PLAYS, LEARNS
- RELATED_TO (family), FRIENDS_WITH, KNOWS
- READS, WATCHES, LISTENS_TO
- EATS_AT, PREFERS_FOOD

**Health & Wellness:**
- DIAGNOSED_WITH, TAKES_MEDICATION, TREATS
- EXERCISES_WITH, TRAINS_FOR
- PRESCRIBED_BY, SEEING_DOCTOR

**Financial:**
- OWNS, PURCHASED, SUBSCRIBED_TO
- COSTS, PAID_FOR, INVESTED_IN
- RENEWED_ON, CANCELLED

**Education:**
- ENROLLED_IN, COMPLETED, STUDYING
- CERTIFIED_IN, QUALIFIED_FOR
- TEACHES, MENTORS, LEARNS_FROM

**Goals & Habits:**
- WORKING_TOWARDS, ACHIEVED, PURSUING
- DOES_DAILY, DOES_WEEKLY, ROUTINELY_PERFORMS
- WANTS_TO, PLANS_TO, CONSIDERING

Format your response as JSON with entities and relationships:

Examples:

Input: "My name is John and I work at Tesla"
Output:
{
    "entities": [
        {"name": "John", "type": "Person"},
        {"name": "Tesla", "type": "Organization"}
    ],
    "relationships": [
        {"from": "John", "to": "Tesla", "type": "WORKS_AT"}
    ]
}

Input: "I'm working on the Cybertruck project"
Output:
{
    "entities": [
        {"name": "Cybertruck", "type": "Project"}
    ],
    "relationships": [
        {"from": "Person", "to": "Cybertruck", "type": "WORKS_ON"}
    ]
}

Input: "My colleague Sarah leads the battery team"
Output:
{
    "entities": [
        {"name": "Sarah", "type": "Person"},
        {"name": "battery team", "type": "Team"}
    ],
    "relationships": [
        {"from": "Sarah", "to": "battery team", "type": "LEADS"}
    ]
}

Input: "I live on the north side of Indianapolis"
Output:
{
    "entities": [
        {"name": "Indianapolis", "type": "Location"},
        {"name": "north side of Indianapolis", "type": "Location"}
    ],
    "relationships": [
        {"from": "Person", "to": "north side of Indianapolis", "type": "LIVES_IN"},
        {"from": "north side of Indianapolis", "to": "Indianapolis", "type": "PART_OF"}
    ]
}

Input: "I live and work on the north side of town" (Context: User's company is in Indianapolis)
Output:
{
    "entities": [
        {"name": "Indianapolis", "type": "Location"},
        {"name": "north side of Indianapolis", "type": "Location"}
    ],
    "relationships": [
        {"from": "Person", "to": "north side of Indianapolis", "type": "LIVES_IN"},
        {"from": "Person", "to": "north side of Indianapolis", "type": "WORKS_FROM"},
        {"from": "north side of Indianapolis", "to": "Indianapolis", "type": "PART_OF"}
    ]
}

Input: "I used the Microsoft Graph API to query stale Intune devices for Acme Corp"
Output:
{
    "entities": [
        {"name": "Microsoft Graph API", "type": "Tool"},
        {"name": "Intune", "type": "Platform"},
        {"name": "Acme Corp", "type": "Client"},
        {"name": "stale Intune devices", "type": "Resource"}
    ],
    "relationships": [
        {"from": "Person", "to": "Microsoft Graph API", "type": "USES_TOOL"},
        {"from": "Microsoft Graph API", "to": "stale Intune devices", "type": "QUERIES"},
        {"from": "stale Intune devices", "to": "Intune", "type": "MANAGED_BY"},
        {"from": "stale Intune devices", "to": "Acme Corp", "type": "BELONGS_TO"}
    ]
}

Input: "I deployed an Azure Function with Python to automate Office 365 license reporting"
Output:
{
    "entities": [
        {"name": "Azure Function", "type": "Platform"},
        {"name": "Python", "type": "Technology"},
        {"name": "Office 365 license reporting", "type": "Action"},
        {"name": "Office 365", "type": "Platform"}
    ],
    "relationships": [
        {"from": "Person", "to": "Azure Function", "type": "DEPLOYED"},
        {"from": "Azure Function", "to": "Python", "type": "USES"},
        {"from": "Azure Function", "to": "Office 365 license reporting", "type": "AUTOMATES"},
        {"from": "Office 365 license reporting", "to": "Office 365", "type": "TARGETS"}
    ]
}

Input: "I configured FSLogix App Masking for the kiosk environment at Smith Industries"
Output:
{
    "entities": [
        {"name": "FSLogix App Masking", "type": "Tool"},
        {"name": "kiosk environment", "type": "Environment"},
        {"name": "Smith Industries", "type": "Client"}
    ],
    "relationships": [
        {"from": "Person", "to": "FSLogix App Masking", "type": "CONFIGURED"},
        {"from": "FSLogix App Masking", "to": "kiosk environment", "type": "APPLIED_TO"},
        {"from": "kiosk environment", "to": "Smith Industries", "type": "BELONGS_TO"}
    ]
}

Input: "I ran a PowerShell script to cross-reference AD, Entra ID, and CrowdStrike data"
Output:
{
    "entities": [
        {"name": "PowerShell script", "type": "Action"},
        {"name": "PowerShell", "type": "Tool"},
        {"name": "Active Directory", "type": "Platform"},
        {"name": "Entra ID", "type": "Platform"},
        {"name": "CrowdStrike", "type": "Platform"}
    ],
    "relationships": [
        {"from": "Person", "to": "PowerShell script", "type": "EXECUTED"},
        {"from": "PowerShell script", "to": "PowerShell", "type": "USES"},
        {"from": "PowerShell script", "to": "Active Directory", "type": "QUERIES"},
        {"from": "PowerShell script", "to": "Entra ID", "type": "QUERIES"},
        {"from": "PowerShell script", "to": "CrowdStrike", "type": "QUERIES"}
    ]
}

Input: "I scheduled the Azure AD Connect sync to run every 30 minutes"
Output:
{
    "entities": [
        {"name": "Azure AD Connect sync", "type": "Action"},
        {"name": "Azure AD Connect", "type": "Tool"},
        {"name": "every 30 minutes", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Person", "to": "Azure AD Connect sync", "type": "SCHEDULED"},
        {"from": "Azure AD Connect sync", "to": "Azure AD Connect", "type": "USES"},
        {"from": "Azure AD Connect sync", "to": "every 30 minutes", "type": "RUNS_AT"}
    ]
}

Input: "The client's Office 365 E3 licenses expire on December 15, 2025"
Output:
{
    "entities": [
        {"name": "Client", "type": "Organization"},
        {"name": "Office 365 E3 licenses", "type": "Resource"},
        {"name": "December 15, 2025", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Client", "to": "Office 365 E3 licenses", "type": "HAS"},
        {"from": "Office 365 E3 licenses", "to": "December 15, 2025", "type": "EXPIRES_ON"}
    ]
}

Input: "I set up a maintenance window every Tuesday from 2am to 4am for server patching"
Output:
{
    "entities": [
        {"name": "maintenance window", "type": "Action"},
        {"name": "every Tuesday 2am-4am", "type": "Temporal"},
        {"name": "server patching", "type": "Action"},
        {"name": "servers", "type": "Device"}
    ],
    "relationships": [
        {"from": "Person", "to": "maintenance window", "type": "CREATED"},
        {"from": "maintenance window", "to": "every Tuesday 2am-4am", "type": "SCHEDULED_FOR"},
        {"from": "maintenance window", "to": "server patching", "type": "FOR_PURPOSE"},
        {"from": "server patching", "to": "servers", "type": "TARGETS"}
    ]
}

Input: "I troubleshot wireless connectivity on Dell Latitude laptops by updating Intel drivers"
Output:
{
    "entities": [
        {"name": "wireless connectivity issue", "type": "Issue"},
        {"name": "Dell Latitude laptops", "type": "Device"},
        {"name": "Intel drivers", "type": "Resource"},
        {"name": "driver update", "type": "Action"}
    ],
    "relationships": [
        {"from": "Person", "to": "wireless connectivity issue", "type": "TROUBLESHOT"},
        {"from": "wireless connectivity issue", "to": "Dell Latitude laptops", "type": "AFFECTS"},
        {"from": "wireless connectivity issue", "to": "driver update", "type": "RESOLVED_BY"},
        {"from": "driver update", "to": "Intel drivers", "type": "UPDATES"}
    ]
}

Input: "I prefer using the Az PowerShell module over Azure CLI for automation scripts"
Output:
{
    "entities": [
        {"name": "Az PowerShell module", "type": "Tool"},
        {"name": "Azure CLI", "type": "Tool"},
        {"name": "automation scripts", "type": "Action"}
    ],
    "relationships": [
        {"from": "Person", "to": "Az PowerShell module", "type": "PREFERS_TOOL"},
        {"from": "Az PowerShell module", "to": "automation scripts", "type": "USED_FOR"},
        {"from": "Person", "to": "Azure CLI", "type": "ALTERNATIVE_TO"}
    ]
}

Input: "I created an Intune dynamic group for Windows 11 devices in the finance department"
Output:
{
    "entities": [
        {"name": "Intune dynamic group", "type": "Resource"},
        {"name": "Intune", "type": "Platform"},
        {"name": "Windows 11 devices", "type": "Device"},
        {"name": "finance department", "type": "Department"}
    ],
    "relationships": [
        {"from": "Person", "to": "Intune dynamic group", "type": "CREATED"},
        {"from": "Intune dynamic group", "to": "Intune", "type": "MANAGED_BY"},
        {"from": "Intune dynamic group", "to": "Windows 11 devices", "type": "CONTAINS"},
        {"from": "Windows 11 devices", "to": "finance department", "type": "BELONGS_TO"}
    ]
}

Input: "I deployed Azure Container Apps for hosting our client portal microservices"
Output:
{
    "entities": [
        {"name": "Azure Container Apps", "type": "Platform"},
        {"name": "client portal", "type": "Project"},
        {"name": "microservices", "type": "Technology"}
    ],
    "relationships": [
        {"from": "Person", "to": "Azure Container Apps", "type": "DEPLOYED"},
        {"from": "Azure Container Apps", "to": "client portal", "type": "HOSTS"},
        {"from": "client portal", "to": "microservices", "type": "USES"}
    ]
}

Input: "I ran Get-ADComputer in PowerShell to audit stale computer accounts older than 90 days"
Output:
{
    "entities": [
        {"name": "Get-ADComputer", "type": "Tool"},
        {"name": "PowerShell", "type": "Tool"},
        {"name": "stale computer accounts", "type": "Resource"},
        {"name": "Active Directory", "type": "Platform"},
        {"name": "90 days", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Person", "to": "Get-ADComputer", "type": "EXECUTED"},
        {"from": "Get-ADComputer", "to": "PowerShell", "type": "RUNS_IN"},
        {"from": "Get-ADComputer", "to": "stale computer accounts", "type": "QUERIES"},
        {"from": "stale computer accounts", "to": "Active Directory", "type": "STORED_IN"},
        {"from": "stale computer accounts", "to": "90 days", "type": "OLDER_THAN"}
    ]
}

Input: "I used CrowdStrike Falcon's RTR to remotely remediate the infected machine"
Output:
{
    "entities": [
        {"name": "CrowdStrike Falcon", "type": "Platform"},
        {"name": "RTR", "type": "Tool"},
        {"name": "infected machine", "type": "Device"},
        {"name": "remediation", "type": "Action"}
    ],
    "relationships": [
        {"from": "Person", "to": "RTR", "type": "USES_TOOL"},
        {"from": "RTR", "to": "CrowdStrike Falcon", "type": "PART_OF"},
        {"from": "RTR", "to": "remediation", "type": "PERFORMS"},
        {"from": "remediation", "to": "infected machine", "type": "TARGETS"}
    ]
}

Input: "I wrote a Logic App to handle Microsoft Graph API throttling for bulk operations"
Output:
{
    "entities": [
        {"name": "Logic App", "type": "Tool"},
        {"name": "Azure Logic Apps", "type": "Platform"},
        {"name": "Microsoft Graph API", "type": "Platform"},
        {"name": "API throttling", "type": "Issue"},
        {"name": "bulk operations", "type": "Action"}
    ],
    "relationships": [
        {"from": "Person", "to": "Logic App", "type": "CREATED"},
        {"from": "Logic App", "to": "Azure Logic Apps", "type": "RUNS_ON"},
        {"from": "Logic App", "to": "API throttling", "type": "HANDLES"},
        {"from": "API throttling", "to": "Microsoft Graph API", "type": "CAUSED_BY"},
        {"from": "Logic App", "to": "bulk operations", "type": "ENABLES"}
    ]
}

Input: "I configured hybrid Azure AD join for workstations at three different client locations"
Output:
{
    "entities": [
        {"name": "hybrid Azure AD join", "type": "Configuration"},
        {"name": "Azure AD", "type": "Platform"},
        {"name": "workstations", "type": "Device"},
        {"name": "three client locations", "type": "Location"}
    ],
    "relationships": [
        {"from": "Person", "to": "hybrid Azure AD join", "type": "CONFIGURED"},
        {"from": "hybrid Azure AD join", "to": "Azure AD", "type": "USES"},
        {"from": "hybrid Azure AD join", "to": "workstations", "type": "APPLIED_TO"},
        {"from": "workstations", "to": "three client locations", "type": "LOCATED_IN"}
    ]
}

Input: "Yesterday I migrated 50 mailboxes from on-prem Exchange to Exchange Online"
Output:
{
    "entities": [
        {"name": "mailbox migration", "type": "Action"},
        {"name": "50 mailboxes", "type": "Resource"},
        {"name": "on-premises Exchange", "type": "Platform"},
        {"name": "Exchange Online", "type": "Platform"},
        {"name": "yesterday", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Person", "to": "mailbox migration", "type": "PERFORMED"},
        {"from": "mailbox migration", "to": "yesterday", "type": "OCCURRED_ON"},
        {"from": "mailbox migration", "to": "50 mailboxes", "type": "MIGRATED"},
        {"from": "50 mailboxes", "to": "on-premises Exchange", "type": "SOURCE"},
        {"from": "50 mailboxes", "to": "Exchange Online", "type": "DESTINATION"}
    ]
}

**Additional General Purpose Examples:**

Input: "I'm reading 'Atomic Habits' and trying to build a morning workout routine"
Output:
{
    "entities": [
        {"name": "Atomic Habits", "type": "Media"},
        {"name": "morning workout routine", "type": "Habit"},
        {"name": "workout", "type": "Health"}
    ],
    "relationships": [
        {"from": "Person", "to": "Atomic Habits", "type": "READS"},
        {"from": "Person", "to": "morning workout routine", "type": "BUILDING"},
        {"from": "morning workout routine", "to": "workout", "type": "INCLUDES"}
    ]
}

Input: "My daughter Sarah is taking piano lessons at Harmony Music School every Wednesday"
Output:
{
    "entities": [
        {"name": "Sarah", "type": "Person"},
        {"name": "piano lessons", "type": "Course"},
        {"name": "Harmony Music School", "type": "Institution"},
        {"name": "every Wednesday", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Person", "to": "Sarah", "type": "PARENT_OF"},
        {"from": "Sarah", "to": "piano lessons", "type": "ENROLLED_IN"},
        {"from": "piano lessons", "to": "Harmony Music School", "type": "LOCATED_AT"},
        {"from": "piano lessons", "to": "every Wednesday", "type": "SCHEDULED_FOR"}
    ]
}

Input: "I'm allergic to shellfish and prefer vegan restaurants"
Output:
{
    "entities": [
        {"name": "shellfish allergy", "type": "Health"},
        {"name": "shellfish", "type": "Food"},
        {"name": "vegan restaurants", "type": "Venue"}
    ],
    "relationships": [
        {"from": "Person", "to": "shellfish allergy", "type": "HAS"},
        {"from": "shellfish allergy", "to": "shellfish", "type": "ALLERGIC_TO"},
        {"from": "Person", "to": "vegan restaurants", "type": "PREFERS"}
    ]
}

Input: "My dentist Dr. Miller is at 123 Oak Street and I see him every 6 months"
Output:
{
    "entities": [
        {"name": "Dr. Miller", "type": "Person"},
        {"name": "dentist", "type": "Health"},
        {"name": "123 Oak Street", "type": "Address"},
        {"name": "every 6 months", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Person", "to": "Dr. Miller", "type": "SEEING_DOCTOR"},
        {"from": "Dr. Miller", "to": "dentist", "type": "WORKS_AS"},
        {"from": "Dr. Miller", "to": "123 Oak Street", "type": "LOCATED_AT"},
        {"from": "Person", "to": "Dr. Miller", "type": "VISITS"},
        {"from": "Person", "to": "every 6 months", "type": "VISITS_FREQUENCY"}
    ]
}

Input: "I have a Netflix subscription that costs $15.99 per month and renews on the 5th"
Output:
{
    "entities": [
        {"name": "Netflix subscription", "type": "Service"},
        {"name": "Netflix", "type": "Organization"},
        {"name": "$15.99 per month", "type": "Transaction"},
        {"name": "5th of each month", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Person", "to": "Netflix subscription", "type": "SUBSCRIBED_TO"},
        {"from": "Netflix subscription", "to": "Netflix", "type": "PROVIDED_BY"},
        {"from": "Netflix subscription", "to": "$15.99 per month", "type": "COSTS"},
        {"from": "Netflix subscription", "to": "5th of each month", "type": "RENEWS_ON"}
    ]
}

Input: "I'm learning Spanish using Duolingo for my trip to Barcelona next summer"
Output:
{
    "entities": [
        {"name": "Spanish", "type": "Skill"},
        {"name": "Duolingo", "type": "Tool"},
        {"name": "Barcelona", "type": "Location"},
        {"name": "next summer", "type": "Temporal"},
        {"name": "trip to Barcelona", "type": "Event"}
    ],
    "relationships": [
        {"from": "Person", "to": "Spanish", "type": "LEARNING"},
        {"from": "Person", "to": "Duolingo", "type": "USES_TOOL"},
        {"from": "Duolingo", "to": "Spanish", "type": "TEACHES"},
        {"from": "Person", "to": "trip to Barcelona", "type": "PLANNING"},
        {"from": "trip to Barcelona", "to": "Barcelona", "type": "DESTINATION"},
        {"from": "trip to Barcelona", "to": "next summer", "type": "SCHEDULED_FOR"}
    ]
}

Input: "I ordered a standing desk from Amazon for $450, order #12345, arriving Friday"
Output:
{
    "entities": [
        {"name": "standing desk", "type": "Product"},
        {"name": "Amazon", "type": "Organization"},
        {"name": "$450", "type": "Transaction"},
        {"name": "order #12345", "type": "Transaction"},
        {"name": "Friday", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Person", "to": "standing desk", "type": "ORDERED"},
        {"from": "standing desk", "to": "Amazon", "type": "PURCHASED_FROM"},
        {"from": "standing desk", "to": "$450", "type": "COSTS"},
        {"from": "standing desk", "to": "order #12345", "type": "ORDER_NUMBER"},
        {"from": "standing desk", "to": "Friday", "type": "ARRIVING_ON"}
    ]
}

Input: "My goal is to run a marathon by December, currently training 4 days a week"
Output:
{
    "entities": [
        {"name": "run a marathon", "type": "Goal"},
        {"name": "marathon", "type": "Event"},
        {"name": "December", "type": "Temporal"},
        {"name": "training", "type": "Habit"},
        {"name": "4 days a week", "type": "Temporal"}
    ],
    "relationships": [
        {"from": "Person", "to": "run a marathon", "type": "WORKING_TOWARDS"},
        {"from": "run a marathon", "to": "December", "type": "TARGET_DATE"},
        {"from": "Person", "to": "training", "type": "DOING"},
        {"from": "training", "to": "4 days a week", "type": "FREQUENCY"},
        {"from": "training", "to": "run a marathon", "type": "PREPARES_FOR"}
    ]
}

Input: "I watch The Office every night before bed, it helps me relax"
Output:
{
    "entities": [
        {"name": "The Office", "type": "Media"},
        {"name": "evening routine", "type": "Habit"},
        {"name": "relaxation", "type": "Goal"}
    ],
    "relationships": [
        {"from": "Person", "to": "The Office", "type": "WATCHES"},
        {"from": "The Office", "to": "evening routine", "type": "PART_OF"},
        {"from": "The Office", "to": "relaxation", "type": "HELPS_WITH"}
    ]
}

Input: "I take my medication Lipitor 20mg every morning with breakfast"
Output:
{
    "entities": [
        {"name": "Lipitor 20mg", "type": "Health"},
        {"name": "medication routine", "type": "Habit"},
        {"name": "every morning", "type": "Temporal"},
        {"name": "breakfast", "type": "Event"}
    ],
    "relationships": [
        {"from": "Person", "to": "Lipitor 20mg", "type": "TAKES_MEDICATION"},
        {"from": "Lipitor 20mg", "to": "every morning", "type": "TAKEN_AT"},
        {"from": "Lipitor 20mg", "to": "breakfast", "type": "TAKEN_WITH"}
    ]
}

Input: "My brother Mark lives in Seattle and works as a software engineer at Microsoft"
Output:
{
    "entities": [
        {"name": "Mark", "type": "Person"},
        {"name": "Seattle", "type": "Location"},
        {"name": "software engineer", "type": "Skill"},
        {"name": "Microsoft", "type": "Organization"}
    ],
    "relationships": [
        {"from": "Person", "to": "Mark", "type": "SIBLING_OF"},
        {"from": "Mark", "to": "Seattle", "type": "LIVES_IN"},
        {"from": "Mark", "to": "software engineer", "type": "WORKS_AS"},
        {"from": "Mark", "to": "Microsoft", "type": "WORKS_AT"}
    ]
}

Input: "I play tennis twice a week at Riverside Courts with my friend Tom"
Output:
{
    "entities": [
        {"name": "tennis", "type": "Hobby"},
        {"name": "twice a week", "type": "Temporal"},
        {"name": "Riverside Courts", "type": "Venue"},
        {"name": "Tom", "type": "Person"}
    ],
    "relationships": [
        {"from": "Person", "to": "tennis", "type": "PLAYS"},
        {"from": "tennis", "to": "twice a week", "type": "FREQUENCY"},
        {"from": "tennis", "to": "Riverside Courts", "type": "PLAYED_AT"},
        {"from": "Person", "to": "Tom", "type": "PLAYS_WITH"},
        {"from": "Person", "to": "Tom", "type": "FRIENDS_WITH"}
    ]
}

Extract all entities and relationships from the conversation. Return valid JSON only.
"""

CUSTOM_UPDATE_MEMORY_PROMPT = """You are a smart memory manager which controls the memory of a system.
You can perform four operations: (1) add into the memory, (2) update the memory, (3) delete from the memory, and (4) no change.

Based on the above four operations, the memory will change.

Compare newly retrieved facts with the existing memory. For each new fact, decide whether to:
- ADD: Add it to the memory as a new element
- UPDATE: Update an existing memory element
- DELETE: Delete an existing memory element
- NONE: Make no change (if the fact is already present or irrelevant)

**CRITICAL RULES FOR PRESERVING DETAIL:**
1. ALWAYS keep the fact with MORE specificity and detail
2. NEVER simplify or generalize location information (neighborhoods, sides of town, districts, addresses)
3. When comparing similar facts, keep the one that contains MORE information, not less
4. "Lives on north side of Indianapolis" is MORE detailed than "Lives in Indianapolis" - KEEP THE DETAILED VERSION
5. "Office near 5th and Main" is MORE detailed than "Office downtown" - KEEP THE DETAILED VERSION
6. If both old and new facts have different details, COMBINE them into one fact with all details

There are specific guidelines to select which operation to perform:

1. **Add**: If the retrieved facts contain new information not present in the memory, then you have to add it by generating a new ID in the id field.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "User is a software engineer"
            }
        ]
    - Retrieved facts: ["Name is John"]
    - New Memory:
        {
            "memory" : [
                {
                    "id" : "0",
                    "text" : "User is a software engineer",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "Name is John",
                    "event" : "ADD"
                }
            ]

        }

2. **Update**: If the retrieved facts contain information that is already present in the memory but the information is totally different, then you have to update it.
**CRITICAL**: If the retrieved fact contains information that conveys the same thing as the elements present in the memory, then you MUST keep the fact which has the MOST SPECIFIC information and detail.
Example (a) -- if the memory contains "User likes to play cricket" and the retrieved fact is "Loves to play cricket with friends", then update the memory with the retrieved facts because it adds "with friends".
Example (b) -- if the memory contains "Likes cheese pizza" and the retrieved fact is "Loves cheese pizza", then you do not need to update it because they convey the same information with the same level of detail.
**Example (c) -- if the memory contains "Lives on north side of Indianapolis" and the retrieved fact is "Lives in Indianapolis", DO NOT UPDATE because the existing memory has MORE detail (specifies "north side"). Keep the existing detailed memory.**
**Example (d) -- if the memory contains "Lives in Indianapolis" and the retrieved fact is "Lives on north side of Indianapolis", UPDATE to the more detailed version because it adds neighborhood specificity.**
If the direction is to update the memory, then you have to update it.
Please keep in mind while updating you have to keep the same ID.
Please note to return the IDs in the output from the input IDs only and do not generate any new ID.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "Lives on north side of Indianapolis"
            },
            {
                "id" : "1",
                "text" : "User is a software engineer"
            },
            {
                "id" : "2",
                "text" : "User likes to play cricket"
            }
        ]
    - Retrieved facts: ["Lives in Indianapolis", "Loves to play cricket with friends"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "Lives on north side of Indianapolis",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "User is a software engineer",
                    "event" : "NONE"
                },
                {
                    "id" : "2",
                    "text" : "Loves to play cricket with friends",
                    "event" : "UPDATE",
                    "old_memory" : "User likes to play cricket"
                }
            ]
        }


3. **Delete**: If the retrieved facts contain information that contradicts the information present in the memory, then you have to delete it. Or if the direction is to delete the memory, then you have to delete it.
Please note to return the IDs in the output from the input IDs only and do not generate any new ID.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "Name is John"
            },
            {
                "id" : "1",
                "text" : "Loves cheese pizza"
            }
        ]
    - Retrieved facts: ["Dislikes cheese pizza"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "Name is John",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "Loves cheese pizza",
                    "event" : "DELETE"
                }
        ]
        }

4. **No Change**: If the retrieved facts contain information that is already present in the memory, then you do not need to make any changes.
- **Example**:
    - Old Memory:
        [
            {
                "id" : "0",
                "text" : "Name is John"
            },
            {
                "id" : "1",
                "text" : "Loves cheese pizza"
            }
        ]
    - Retrieved facts: ["Name is John"]
    - New Memory:
        {
        "memory" : [
                {
                    "id" : "0",
                    "text" : "Name is John",
                    "event" : "NONE"
                },
                {
                    "id" : "1",
                    "text" : "Loves cheese pizza",
                    "event" : "NONE"
                }
            ]
        }
"""


class PydanticAIAgent:
    """
    Main agent class integrating Pydantic AI, Mem0, Langfuse, and Guardrails
    """

    def __init__(self):
        """Initialize the agent with all integrations"""
        logger.info("Initializing Pydantic AI Agent...")

        # Validate configuration
        if not config.validate():
            raise ValueError("Invalid configuration. Please check your environment variables.")

        # Display configuration
        config.display()

        # Initialize Ollama model (via OpenAI-compatible endpoint)
        # Use simple model string for pydantic-ai 1.x
        self.model = f"openai:{config.OLLAMA_MODEL}"

        # Get system prompt
        system_prompt = get_system_prompt(config.AGENT_PROMPT_TEMPLATE)

        # Initialize Pydantic AI Agent
        self.agent = Agent(
            model=self.model,
            system_prompt=system_prompt,
        )

        # Initialize Mem0 for long-term memory
        self.memory = self._initialize_memory()

        # Initialize Langfuse for observability
        self.langfuse = self._initialize_langfuse()

        # Initialize Guardrails - disabled for now
        # self.guard = self._initialize_guardrails()
        self.guard = None

        # Session metadata
        self.session_metadata = create_conversation_metadata(config.MEM0_USER_ID)

        logger.info("Agent initialization complete!")

    def _initialize_memory(self) -> Optional[HybridMemoryManager]:
        """
        Initialize Hybrid Memory Manager (mem0 for vectors + Graphiti for graph)

        Returns:
            HybridMemoryManager instance or None if initialization fails
        """
        try:
            # mem0 config (vector store only, no graph)
            # Use OpenAI for LLM (better instruction following for custom prompts)
            # Use Ollama for embeddings (fast and local)
            mem0_config = {
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": "gpt-4o-mini",  # Cost-effective for fact extraction
                        "api_key": config.OPENAI_GRAPH_API_KEY,
                        "openai_base_url": "https://api.openai.com/v1",  # Explicit base URL
                        "temperature": 0.1,  # Low temp for consistent fact extraction
                    }
                },
                "vector_store": {
                    "provider": "pgvector",
                    "config": {
                        "dbname": config.POSTGRES_DB,
                        "user": config.POSTGRES_USER,
                        "password": config.POSTGRES_PASSWORD,
                        "host": config.POSTGRES_HOST,
                        "port": config.POSTGRES_PORT,
                        "embedding_model_dims": 768,
                    }
                },
                "embedder": {
                    "provider": "ollama",
                    "config": {
                        "model": "nomic-embed-text:latest",
                        "ollama_base_url": config.OLLAMA_HOST,
                        "embedding_dims": 768,
                    }
                },
                "custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT,
                "custom_update_memory_prompt": CUSTOM_UPDATE_MEMORY_PROMPT,
            }

            # Create hybrid memory manager
            hybrid_memory = HybridMemoryManager(
                mem0_config=mem0_config,
                neo4j_uri=config.NEO4J_URI,
                neo4j_username=config.NEO4J_USERNAME,
                neo4j_password=config.NEO4J_PASSWORD,
                openai_api_key=config.OPENAI_GRAPH_API_KEY
            )

            logger.info("Hybrid Memory Manager created (not initialized yet - call initialize_memory_async())")
            return hybrid_memory

        except Exception as e:
            logger.error(f"Failed to create Hybrid Memory Manager: {e}")
            print_system_message(f"Warning: Memory system unavailable - {e}", "yellow")
            return None

    async def initialize_memory_async(self) -> None:
        """
        Async initialization of the hybrid memory system.
        Must be called after __init__().
        """
        if self.memory is None:
            logger.warning("Memory not created, skipping async initialization")
            return

        try:
            logger.info("Initializing hybrid memory (async)...")
            await self.memory.initialize()
            logger.info("Hybrid memory initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initialize hybrid memory: {e}", exc_info=True)
            self.memory = None

    def _initialize_langfuse(self) -> Optional[Langfuse]:
        """
        Initialize Langfuse for observability

        Returns:
            Langfuse instance or None if disabled/failed
        """
        if not config.LANGFUSE_ENABLED:
            logger.info("Langfuse observability is disabled")
            return None

        if not config.LANGFUSE_PUBLIC_KEY or not config.LANGFUSE_SECRET_KEY:
            logger.warning("Langfuse keys not configured, skipping observability")
            return None

        try:
            langfuse = Langfuse(
                public_key=config.LANGFUSE_PUBLIC_KEY,
                secret_key=config.LANGFUSE_SECRET_KEY,
                host=config.LANGFUSE_HOST,
            )
            logger.info("Langfuse initialized successfully")
            return langfuse

        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            print_system_message(f"Warning: Observability unavailable - {e}", "yellow")
            return None

    # def _initialize_guardrails(self) -> Optional[Guard]:
    #     """
    #     Initialize Guardrails AI
    #
    #     Returns:
    #         Guard instance or None if disabled/failed
    #     """
    #     if not config.GUARDRAILS_ENABLED:
    #         logger.info("Guardrails AI is disabled")
    #         return None
    #
    #     try:
    #         if ToxicLanguage is None:
    #             logger.warning("ToxicLanguage validator not available, skipping Guardrails")
    #             return None
    #
    #         # Initialize with toxic language detection
    #         guard = Guard().use(
    #             ToxicLanguage,
    #             threshold=0.5,
    #             validation_method="sentence",
    #             on_fail="exception"
    #         )
    #         logger.info("Guardrails AI initialized successfully")
    #         return guard
    #
    #     except Exception as e:
    #         logger.error(f"Failed to initialize Guardrails: {e}")
    #         print_system_message(f"Warning: Guardrails unavailable - {e}", "yellow")
    #         return None

    def _get_ntp_time(self) -> Optional[float]:
        """
        Get current time from NTP server (us.pool.ntp.org).

        Returns:
            Unix timestamp from NTP server, or None if NTP query fails
        """
        if ntplib is None:
            logger.warning("ntplib not available. Using system time as fallback.")
            return None

        try:
            ntp_client = ntplib.NTPClient()

            # Query US NTP pool with 3 second timeout
            response = ntp_client.request('us.pool.ntp.org', version=3, timeout=3)

            # Get the NTP time
            ntp_time = response.tx_time

            logger.info(f"Successfully synced with NTP server us.pool.ntp.org")
            return ntp_time

        except Exception as e:
            logger.warning(f"Failed to sync with NTP server: {e}. Using system time as fallback.")
            return None

    async def _get_user_timezone(self, location_context: dict | None = None) -> str:
        """
        Retrieve user's timezone preference from IP geolocation or Hybrid memory.

        Priority:
        1. IP geolocation timezone (from location_context)
        2. Explicit timezone strings from memory (e.g., "America/New_York")
        3. City names from memory (e.g., "Indianapolis", "New York")

        Args:
            location_context: Optional location data from IP geolocation
                             {city, state, country, timezone, latitude, longitude}

        Returns:
            Timezone string (e.g., 'America/New_York') or 'UTC' if not found
        """
        # PRIORITY 1: Check location_context from IP geolocation first
        if location_context and location_context.get('timezone'):
            timezone_str = location_context['timezone']
            try:
                # Validate the timezone
                pytz.timezone(timezone_str)
                logger.info(f"Using timezone from IP geolocation: {timezone_str}")
                return timezone_str
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Invalid timezone from IP geolocation: {timezone_str}, falling back to memory")

        # PRIORITY 2 & 3: Fall back to memory-based timezone detection
        if not self.memory:
            return 'UTC'

        # Mapping of common US cities to their IANA timezones
        city_to_timezone = {
            'new york': 'America/New_York',
            'nyc': 'America/New_York',
            'boston': 'America/New_York',
            'philadelphia': 'America/New_York',
            'washington': 'America/New_York',
            'miami': 'America/New_York',
            'atlanta': 'America/New_York',
            'chicago': 'America/Chicago',
            'indianapolis': 'America/Indiana/Indianapolis',
            'dallas': 'America/Chicago',
            'houston': 'America/Chicago',
            'denver': 'America/Denver',
            'phoenix': 'America/Phoenix',
            'los angeles': 'America/Los_Angeles',
            'la': 'America/Los_Angeles',
            'san francisco': 'America/Los_Angeles',
            'sf': 'America/Los_Angeles',
            'seattle': 'America/Los_Angeles',
            'portland': 'America/Los_Angeles',
            'las vegas': 'America/Los_Angeles',
        }

        try:
            # Search memory for timezone information
            logger.info("Searching for user timezone in memory...")
            memories = await self.memory.search(
                query="user timezone preference location city",
                user_id=config.MEM0_USER_ID,
                limit=5
            )

            # Parse memories from hybrid system (returns vector_results + graph_results)
            if memories and isinstance(memories, dict):
                memory_list = memories.get('vector_results', [])
            elif memories and isinstance(memories, list):
                memory_list = memories
            else:
                memory_list = []

            # Look for timezone patterns in memories
            timezone_pattern = r'\b([A-Z][a-z]+/[A-Z][a-z_]+)\b'  # Matches "America/New_York" format

            for mem in memory_list:
                if isinstance(mem, dict):
                    mem_text = mem.get('memory', mem.get('text', str(mem)))
                else:
                    mem_text = str(mem)

                mem_text_lower = mem_text.lower()

                # 1. Check if memory contains explicit timezone information
                if 'timezone' in mem_text_lower or 'time zone' in mem_text_lower:
                    # Try to extract timezone string
                    match = re.search(timezone_pattern, mem_text)
                    if match:
                        timezone_str = match.group(1)
                        # Validate timezone
                        try:
                            pytz.timezone(timezone_str)
                            logger.info(f"Found explicit timezone in memory: {timezone_str}")
                            return timezone_str
                        except pytz.exceptions.UnknownTimeZoneError:
                            logger.warning(f"Invalid timezone found in memory: {timezone_str}")
                            continue

                # 2. Check if memory contains a city name we can map to a timezone
                for city, tz in city_to_timezone.items():
                    if city in mem_text_lower:
                        logger.info(f"Found city '{city}' in memory, mapping to timezone: {tz}")
                        return tz

            # Fallback: Try get_all() to retrieve all memories if search didn't find location
            logger.info("Search didn't find timezone, trying get_all() as fallback...")
            try:
                # Access mem0 directly for get_all (not available in hybrid interface)
                all_memories = self.memory.mem0.get_all(user_id=config.MEM0_USER_ID) if self.memory.mem0 else None
                if all_memories:
                    if isinstance(all_memories, dict):
                        all_memory_list = all_memories.get('results', [])
                    elif isinstance(all_memories, list):
                        all_memory_list = all_memories
                    else:
                        all_memory_list = []

                    for mem in all_memory_list:
                        if isinstance(mem, dict):
                            mem_text = mem.get('memory', mem.get('text', str(mem)))
                        else:
                            mem_text = str(mem)

                        mem_text_lower = mem_text.lower()

                        # Check for city names in all memories
                        for city, tz in city_to_timezone.items():
                            if city in mem_text_lower:
                                logger.info(f"Found city '{city}' in fallback memory check, mapping to timezone: {tz}")
                                return tz

                logger.info("No valid timezone found in all memories")
            except Exception as fallback_error:
                logger.warning(f"Fallback memory retrieval failed: {fallback_error}")

            logger.info("No valid timezone found in memory, using UTC")
            return 'UTC'

        except Exception as e:
            logger.error(f"Error retrieving timezone from memory: {e}", exc_info=True)
            return 'UTC'

    def _get_current_time_context(self, timezone_str: str = 'UTC') -> str:
        """
        Get current date and time context for this specific message.
        Time is synced with us.pool.ntp.org for accuracy.

        Args:
            timezone_str: Timezone string (e.g., 'America/New_York' or 'UTC')

        Returns:
            Time context string with current datetime in the specified timezone
        """
        # Try to get NTP time first, fallback to system time
        ntp_timestamp = self._get_ntp_time()

        if ntp_timestamp:
            # Use NTP time
            now_utc = datetime.fromtimestamp(ntp_timestamp, tz=pytz.UTC)
            time_source = "(synced with us.pool.ntp.org)"
        else:
            # Fallback to system time
            now_utc = datetime.now(pytz.UTC)
            time_source = "(system time)"

        # Convert to user's timezone
        try:
            user_tz = pytz.timezone(timezone_str)
            now_local = now_utc.astimezone(user_tz)

            # Format datetime information
            current_datetime = now_local.strftime("%A, %B %d, %Y at %I:%M %p %Z")
            timezone_name = now_local.tzname()

            return f"\n[Context - Current time available if needed]: {current_datetime} in {timezone_name}. Only mention time if the user asks about it or if it's directly relevant to their question.\n"

        except Exception as e:
            logger.error(f"Error converting to timezone {timezone_str}: {e}")
            # Fallback to UTC
            current_datetime = now_utc.strftime("%A, %B %d, %Y at %I:%M %p UTC")
            return f"\n[Context - Current time available if needed]: {current_datetime}. Only mention time if the user asks about it or if it's directly relevant to their question.\n"

    async def _get_memory_context(self, user_input: str) -> str:
        """
        Retrieve relevant memories based on user input using hybrid memory system.

        Args:
            user_input: Current user message

        Returns:
            Memory context string combining vector and graph results
        """
        if not self.memory:
            return ""

        try:
            # Search hybrid memory (both vector and graph)
            logger.info(f"Searching hybrid memory for query: '{user_input}'")
            memories = await self.memory.search(
                query=user_input,
                user_id=config.MEM0_USER_ID,
                limit=3
            )
            logger.info(f"Hybrid memory search returned: {len(memories.get('vector_results', []))} vector results, {len(memories.get('graph_results', []))} graph results")

            # Hybrid memory returns {'vector_results': [...], 'graph_results': [...], 'combined_context': "..."}
            # Use the pre-formatted combined_context from hybrid memory
            if memories and isinstance(memories, dict):
                combined_context = memories.get('combined_context', '')
                if combined_context:
                    logger.info(f"Memory context created from hybrid search")
                    logger.info(f"Returning context (length={len(combined_context)}): {combined_context[:300]}...")
                    return combined_context
                else:
                    logger.warning("No memories found in hybrid search - combined_context is empty")
            else:
                logger.warning("Invalid memory search result format")

        except Exception as e:
            logger.error(f"Error retrieving memories: {e}", exc_info=True)

        return ""

    async def _save_to_memory(self, user_input: str, agent_response: str) -> None:
        """
        Save conversation to hybrid long-term memory (mem0 + Graphiti)

        Args:
            user_input: User message
            agent_response: Agent response
        """
        if not self.memory:
            logger.warning("Memory not initialized, skipping save")
            return

        try:
            logger.info(f"Attempting to save conversation to hybrid memory...")

            # Save to both mem0 (vectors) and Graphiti (graph)
            result = await self.memory.add(
                messages=[
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": agent_response}
                ],
                user_id=config.MEM0_USER_ID,
                agent_id=config.MEM0_AGENT_ID,
                metadata=self.session_metadata,
                infer=True,  # Enable LLM-based fact extraction with custom prompt
            )
            logger.info(f"Conversation saved to hybrid memory. mem0 result: {result.get('mem0')}, graphiti result: {result.get('graphiti')}")

        except Exception as e:
            logger.error(f"Error saving to memory: {e}", exc_info=True)

    async def _save_to_memory_async(self, user_input: str, agent_response: str) -> None:
        """
        Async method for saving conversation to hybrid memory (mem0 + Graphiti).
        Called as a background task to avoid blocking the response stream.

        Args:
            user_input: User message
            agent_response: Agent response
        """
        if not self.memory:
            logger.warning("Memory not initialized, skipping save")
            return

        try:
            logger.info(f"Saving conversation to hybrid memory (async background task)...")

            # Directly await hybrid memory's async add() method
            # Per mem0 documentation, we pass the full conversation (both user and assistant messages)
            # Our custom_prompt should filter out extraction from assistant responses
            result = await self.memory.add(
                messages=[
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": agent_response}
                ],
                user_id=config.MEM0_USER_ID,
                agent_id=config.MEM0_AGENT_ID,
                metadata=self.session_metadata,
                infer=True,  # Enable LLM-based fact extraction with custom prompt
            )

            logger.info(f"Hybrid memory add result: {result}")

            # Log results from both systems
            if isinstance(result, dict):
                # mem0 results (vector store)
                if 'mem0' in result and result['mem0']:
                    mem0_result = result['mem0']
                    if isinstance(mem0_result, dict) and 'results' in mem0_result:
                        logger.info(f"mem0 vector store: {len(mem0_result['results'])} memories")
                    else:
                        logger.info(f"mem0 result: {mem0_result}")

                # Graphiti results (knowledge graph)
                if 'graphiti' in result and result['graphiti']:
                    logger.info(f"Graphiti graph result: {result['graphiti']}")

            logger.info(f"Conversation saved to hybrid memory successfully (background task completed)")

        except Exception as e:
            logger.error(f"Error saving to hybrid memory (async): {e}", exc_info=True)

    # def _validate_with_guardrails(self, text: str) -> bool:
    #     """
    #     Validate text using Guardrails AI
    #
    #     Args:
    #         text: Text to validate
    #
    #     Returns:
    #         True if valid, False otherwise
    #     """
    #     if not self.guard:
    #         return True
    #
    #     try:
    #         self.guard.validate(text)
    #         return True
    #
    #     except Exception as e:
    #         logger.warning(f"Guardrails validation failed: {e}")
    #         return False

    @observe()
    async def process_message(self, user_input: str) -> str:
        """
        Process a user message and return agent response

        Args:
            user_input: User message

        Returns:
            Agent response
        """
        # Sanitize input
        user_input = sanitize_input(user_input)

        # Validate input with guardrails - disabled for now
        # if not self._validate_with_guardrails(user_input):
        #     return "I'm sorry, but I cannot process that message. Please rephrase your request."

        # Get user's timezone from memory (async)
        user_timezone = await self._get_user_timezone()

        # Get current time context (fresh for this message, in user's timezone)
        time_context = self._get_current_time_context(user_timezone)

        # Get memory context from hybrid memory (async)
        memory_context = await self._get_memory_context(user_input)

        # Prepare the full message with context
        full_message = user_input
        if time_context or memory_context:
            context_parts = [time_context, memory_context]
            combined_context = "".join([ctx for ctx in context_parts if ctx])
            full_message = f"{combined_context}\n{user_input}"
            logger.info(f"Full message with context (length={len(full_message)}): {full_message[:400]}...")
        else:
            logger.warning("No context added to message - both time_context and memory_context are empty")

        # Get response from agent
        try:
            result = await self.agent.run(full_message)
            # In pydantic-ai, result.output contains the response
            if hasattr(result, 'output'):
                response = result.output
            elif hasattr(result, 'data'):
                response = result.data
            elif isinstance(result, str):
                response = result
            else:
                # Fallback: convert to string
                response = str(result)

            # Validate response with guardrails - disabled for now
            # if not self._validate_with_guardrails(response):
            #     response = "I apologize, but I need to rephrase my response. Let me try again."

            # Save to hybrid memory (async)
            await self._save_to_memory(user_input, response)

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"I encountered an error: {str(e)}"

    async def process_message_stream(self, user_input: str, location_context: dict | None = None):
        """
        Process a user message and stream the agent response token by token

        This method is used by the FastAPI streaming endpoint to provide
        real-time responses using Server-Sent Events (SSE).

        Args:
            user_input: User message
            location_context: Optional location data from IP geolocation
                             {city, state, country, timezone, latitude, longitude}

        Yields:
            Individual tokens of the agent's response
        """
        try:
            # Sanitize input
            user_input = sanitize_input(user_input)

            # Validate input with guardrails - disabled for now
            # if not self._validate_with_guardrails(user_input):
            #     yield "I'm sorry, but I cannot process that message."
            #     return

            # Get user's timezone - prioritize location_context, fallback to memory (async)
            user_timezone = await self._get_user_timezone(location_context)

            # Get current time context (fresh for this message, in user's timezone)
            time_context = self._get_current_time_context(user_timezone)

            # Get memory context from hybrid memory (async)
            memory_context = await self._get_memory_context(user_input)

            # Prepare the full message with context
            full_message = user_input
            if time_context or memory_context:
                context_parts = [time_context, memory_context]
                combined_context = "".join([ctx for ctx in context_parts if ctx])
                full_message = f"{combined_context}\n{user_input}"
                logger.info(f"[STREAM] Full message with context (length={len(full_message)}): {full_message[:400]}...")
            else:
                logger.warning("[STREAM] No context added to message - both time_context and memory_context are empty")

            logger.info(f"Streaming response for message: {user_input[:50]}...")

            # Stream response from agent
            full_response = ""
            async with self.agent.run_stream(full_message) as result:
                # Stream text deltas (token by token)
                async for text in result.stream_text(delta=True):
                    full_response += text
                    yield text  # Yield each token as it arrives

            logger.info(f"Stream completed. Total length: {len(full_response)}")

            # Validate response with guardrails - disabled for now
            # if not self._validate_with_guardrails(full_response):
            #     yield " [Response was filtered for safety]"

            # Save complete response to memory asynchronously (non-blocking)
            # This runs in the background so it doesn't delay the stream completion signal
            asyncio.create_task(self._save_to_memory_async(user_input, full_response))

        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            yield f"Error: {str(e)}"

    async def run_conversation_loop(self) -> None:
        """
        Run the main conversation loop
        """
        print_welcome_message(config.AGENT_NAME, config.AGENT_PROMPT_TEMPLATE)

        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                # Check for exit command
                if is_exit_command(user_input):
                    print_system_message("Goodbye! 👋")
                    break

                if not user_input:
                    continue

                # Print user message
                print_user_message(user_input)

                # Process message and get response
                response = await self.process_message(user_input)

                # Print agent response
                print_agent_message(response)

            except KeyboardInterrupt:
                print_system_message("\n\nConversation interrupted. Goodbye! 👋")
                break

            except Exception as e:
                logger.error(f"Error in conversation loop: {e}")
                print_error(str(e))


async def main():
    """Main entry point"""
    try:
        agent = PydanticAIAgent()
        await agent.run_conversation_loop()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print_error(f"Failed to start agent: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
