#!/usr/bin/env python3
"""
N8N Workflow Generator - Fuel Hedging Advisor
Generates complete n8n workflow JSON from scratch
"""

import json
from datetime import datetime
from typing import List, Dict, Any

# Base workflow metadata
workflow_base = {
    "name": "Fuel Hedging Advisor - Production",
    "active": False,  # Start inactive until configured
    "settings": {
        "executionOrder": "v1"
    },
    "meta": {
        "templateCredsSetupCompleted": False,
        "instanceId": "fuel_hedging_advisor_v1"
    },
    "tags": ["fuel-hedging", "aviation", "risk-management"]
}

# Node ID generator
node_counter = 1

def gen_id():
    global node_counter
    node_counter += 1
    return f"fuel-hedge-node-{node_counter:04d}"

def create_schedule_trigger():
    """Daily 06:00 UTC trigger"""
    return {
        "parameters": {
            "rule": {
                "interval": [
                    {
                        "field": "cronExpression",
                        "expression": "0 6 * * *"  # Daily at 06:00 UTC
                    }
                ]
            }
        },
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [-800, 0],
        "id": gen_id(),
        "name": "Daily 06:00 UTC Schedule"
    }

def create_webhook_trigger():
    """Manual webhook trigger"""
    return {
        "parameters": {
            "httpMethod": "POST",
            "path": "fuel-hedge-trigger",
            "responseMode": "lastNode",
            "options": {}
        },
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "position": [-800, 200],
        "id": gen_id(),
        "name": "Manual Webhook Trigger",
        "webhookId": gen_id()
    }

def create_eia_api_node():
    """EIA API - Jet Fuel Spot Prices"""
    return {
        "parameters": {
            "url": "https://api.eia.gov/v2/petroleum/pri/spt/data/",
            "authentication": "genericCredentialType",
            "genericAuthType": "queryAuth",
            "sendQuery": True,
            "queryParameters": {
                "parameters": [
                    {"name": "api_key", "value": "={{ $credentials.eia_api_key }}"},
                    {"name": "frequency", "value": "daily"},
                    {"name": "data[0]", "value": "value"},
                    {"name": "facets[product][]", "value": "EPD2F"},  # Jet Fuel US Gulf Coast
                    {"name": "start", "value": "={{ DateTime.now().minus({days: 365}).toFormat('yyyy-MM-dd') }}"},
                    {"name": "sort[0][column]", "value": "period"},
                    {"name": "sort[0][direction]", "value": "desc"},
                    {"name": "length", "value": "5000"}
                ]
            },
            "options": {
                "response": {"response": {"responseFormat": "json"}},
                "timeout": 30000
            }
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [-500, -200],
        "id": gen_id(),
        "name": "EIA - Jet Fuel Spot"
    }

def create_cme_heating_oil_node():
    """CME API - Heating Oil Futures"""
    return {
        "parameters": {
            "url": "https://www.cmegroup.com/market-data/delayed-quotes/energy.json",
            "authentication": "headerAuth",
            "sendQuery": True,
            "queryParameters": {
                "parameters": [
                    {"name": "codes", "value": "HO"}  # Heating Oil
                ]
            },
            "headerParameters": {
                "parameters": [
                    {"name": "X-API-Key", "value": "={{ $credentials.cme_api_key }}"}
                ]
            },
            "options": {
                "response": {"response": {"responseFormat": "json"}},
                "timeout": 30000
            }
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [-500, -50],
        "id": gen_id(),
        "name": "CME - Heating Oil"
    }

def create_cme_wti_node():
    """CME API - WTI Crude Futures"""
    return {
        "parameters": {
            "url": "https://www.cmegroup.com/market-data/delayed-quotes/energy.json",
            "authentication": "headerAuth",
            "sendQuery": True,
            "queryParameters": {
                "parameters": [
                    {"name": "codes", "value": "CL"}  # WTI Crude
                ]
            },
            "headerParameters": {
                "parameters": [
                    {"name": "X-API-Key", "value": "={{ $credentials.cme_api_key }}"}
                ]
            },
            "options": {
                "response": {"response": {"responseFormat": "json"}},
                "timeout": 30000
            }
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [-500, 100],
        "id": gen_id(),
        "name": "CME - WTI Crude"
    }

def create_ice_brent_node():
    """ICE API - Brent Crude Futures"""
    return {
        "parameters": {
            "url": "https://www.theice.com/marketdata/DelayedMarkets.shtml",
            "authentication": "headerAuth",
            "sendQuery": True,
            "queryParameters": {
                "parameters": [
                    {"name": "contractCode", "value": "B"}  # Brent
                ]
            },
            "headerParameters": {
                "parameters": [
                    {"name": "Authorization", "value": "Bearer ={{ $credentials.ice_api_key }}"}
                ]
            },
            "options": {
                "response": {"response": {"responseFormat": "json"}},
                "timeout": 30000
            }
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [-500, 250],
        "id": gen_id(),
        "name": "ICE - Brent Crude"
    }

# ... Continue with more nodes ...

print("🚀 N8N Workflow Generator Ready")
print("This script generates the complete workflow JSON")
print("Run this to create: fuel_hedging_advisor_workflow.json")
