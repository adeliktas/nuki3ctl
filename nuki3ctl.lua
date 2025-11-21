#!/usr/bin/lua

-- Docs used:
-- https://nuki-shop-prod-eu-content.s3.de.perf.cloud.ovh.net/legacy/2024/10/20241024NukiBridgeAPI1_13_3.pdf

local ok, dkjson = pcall(require, 'dkjson')
if not ok then
    print("The package/module dkjson needs to be installed (<10 Kb)")
    os.exit(1)
end
local os = require 'os'
local io = require 'io'

-- Global variables as requested
nuki_ip = nil
nuki_token = nil
nuki_devices_list = {}  -- Will be populated as list of NukiDevice tables when listing

-- Define default config as a constant for comparison
DEFAULT_CONFIG = {
    ip = '0.0.0.0',
    token = '1mytkn',
    nukiId = '123456789'
}

-- Helper function to check if two tables are equal
local function tables_equal(t1, t2)
    if t1 == t2 then return true end
    for k, v in pairs(t1) do
        if t2[k] ~= v then return false end
    end
    for k, v in pairs(t2) do
        if t1[k] ~= v then return false end
    end
    return true
end

-- Helper function for HTTP GET using curl
local function http_get(url)
    local handle = io.popen('curl -s -w "\\n%{http_code}" "' .. url .. '"')
    local output = handle:read("*a")
    handle:close()
    local body = output:match("^(.*)\n(%d%d%d)$")
    local code = tonumber(output:match("\n(%d%d%d)$"))
    return body, code
end

local function new_NukiDevice(data)
    --[[
    Table representing a Nuki device based on the /list JSON response structure.
    Attributes correspond to the keys in the API response for Smart Lock 3.0.
    ]]
    local self = {}
    self.deviceType = data.deviceType
    self.nukiId = data.nukiId
    self.name = data.name
    self.firmwareVersion = data.firmwareVersion
    self.lastKnownState = data.lastKnownState or {}
    -- Expand lastKnownState attributes for easier access (based on API docs)
    local lks = self.lastKnownState
    if next(lks) ~= nil then  -- Check if not empty
        self.mode = lks.mode
        self.state = lks.state
        self.stateName = lks.stateName
        self.batteryCritical = lks.batteryCritical
        self.batteryCharging = lks.batteryCharging
        self.batteryChargeState = lks.batteryChargeState
        self.keypadBatteryCritical = lks.keypadBatteryCritical
        self.doorsensorState = lks.doorsensorState
        self.doorsensorStateName = lks.doorsensorStateName
        self.timestamp = lks.timestamp
    end
    return self
end

local function load_config()
    --[[
    Load defaults from config.json if it exists, or create a default if not.
    ]]
    local config_path = 'config.json'
    local f_test = io.open(config_path, 'r')
    if not f_test then
        local f, err = io.open(config_path, 'w')
        if not f then
            print("Error creating " .. config_path .. ": " .. err)
            return {}
        end
        f:write(dkjson.encode(DEFAULT_CONFIG, {indent = true}))
        f:close()
        print("Created default " .. config_path .. ". Please edit it with your values.")
    else
        f_test:close()
    end
    
    local config = {}
    local f = io.open(config_path, 'r')
    if f then
        local content = f:read("*a")
        f:close()
        local ok, decoded = pcall(dkjson.decode, content)
        if ok then
            config = decoded
            -- Check if loaded config matches defaults exactly
            if tables_equal(config, DEFAULT_CONFIG) then
                print("Warning: config.json contains default values. Please edit it with your actual settings.")
            end
        else
            print("Warning: config.json is malformed. Ignoring it.")
        end
    end
    return config
end

-- Main logic
local config = load_config()

-- Parse command line arguments
local ip_from_arg = false
local token_from_arg = false
local id_from_arg = false
local action = nil
local i = 1
while i <= #arg do
    if arg[i] == '-i' or arg[i] == '--ip' then
        i = i + 1
        nuki_ip = arg[i]
        ip_from_arg = true
    elseif arg[i] == '-t' or arg[i] == '--token' then
        i = i + 1
        nuki_token = arg[i]
        token_from_arg = true
    elseif arg[i] == '-id' or arg[i] == '--nukiid' then
        i = i + 1
        nuki_id = arg[i]
        id_from_arg = true
    elseif arg[i] == '-h' or arg[i] == '--help' then
        action = 'help'
    else
        action = arg[i]
    end
    i = i + 1
end

-- Apply config overrides if not set by args
nuki_ip = nuki_ip or config.ip
nuki_token = nuki_token or config.token
nuki_id = nuki_id or config.nukiId

-- Warn if using defaults from config
if not ip_from_arg and nuki_ip then
    print("Using default IP from config.json: " .. nuki_ip)
end
if not token_from_arg and nuki_token then
    print("Using default token from config.json: " .. nuki_token)
end
if action ~= 'list' and action ~= 'help' and not id_from_arg and nuki_id then
    print("Using default Nuki ID from config.json: " .. nuki_id)
end

if not nuki_ip or not nuki_token then
    print("IP and token are required (via flags or config.json).")
    os.exit(1)
end

local base_url = "http://" .. nuki_ip .. ":8080"

if action == 'help' or not action then
    print([[Nuki Smart Lock CLI tool using HTTP API (v1.13.3). Defaults from config.json if not overridden.

Usage: lua nuki3ctl.lua [options] [action]

Options:
  -i, --ip        Nuki Bridge IP address (overrides config.json)
  -t, --token     API token (overrides config.json)
  -id, --nukiid   Nuki device ID (overrides config.json)

Actions: open (unlock), close (lock), status (current state), list (all devices)

Example: lua nuki3ctl.lua -i 192.168.107.194 -t 1mytkn -id 123456789 open]])
    os.exit(0)
end

local valid_actions = {open = true, close = true, status = true, list = true}
if not valid_actions[action] then
    print("Invalid action: " .. action)
    os.exit(1)
end

if action == 'list' then
    local url = base_url .. "/list?token=" .. nuki_token
    local body, code = http_get(url)
    if code ~= 200 then
        print("Error listing devices: HTTP " .. (code or "unknown"))
        os.exit(1)
    end
    local ok, devices_data = pcall(dkjson.decode, body)
    if not ok then
        print("Error decoding JSON: " .. devices_data)
        os.exit(1)
    end
    for _, device in ipairs(devices_data) do
        table.insert(nuki_devices_list, new_NukiDevice(device))
    end
    print(dkjson.encode(nuki_devices_list, {indent = true}))
    os.exit(0)
end

if not nuki_id then
    print("Nuki ID is required for actions other than 'list' (via -id or config.json).")
    os.exit(1)
end

local url = nil
if action == 'open' then
    url = base_url .. "/lockAction?nukiId=" .. nuki_id .. "&action=1&token=" .. nuki_token .. "&deviceType=4"
elseif action == 'close' then
    url = base_url .. "/lockAction?nukiId=" .. nuki_id .. "&action=2&token=" .. nuki_token .. "&deviceType=4"
elseif action == 'status' then
    url = base_url .. "/lockState?nukiId=" .. nuki_id .. "&token=" .. nuki_token .. "&deviceType=4"
end

local body, code = http_get(url)
if code ~= 200 then
    print("Error performing " .. action .. ": HTTP " .. (code or "unknown"))
    os.exit(1)
end
local ok, data = pcall(dkjson.decode, body)
if ok then
    print(dkjson.encode(data, {indent = true}))
else
    print("Error decoding JSON: " .. data)
end
