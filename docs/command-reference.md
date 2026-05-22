# Elisity CLI -- Command Reference

> The 436 REST commands below are auto-generated from the Elisity CCC OpenAPI
> specification. The `reporting` group (19 commands) is hand-coded against the
> CCC GraphQL endpoint at `/api/reporting/v1/data` and is NOT listed in this
> reference — see [user-guide.md](user-guide.md) section 9 for the full
> reporting catalog.
>
> **462 commands** total: 436 auto-generated REST + 19 hand-coded GraphQL
> reporting + 7 CLI-native (auth + config). 11 groups total.

## Quick Find by Operation Type

### List / Get operations (154 commands)

| Group | Command | Description |
|-------|---------|-------------|
| ad | `agent-manifest` | Get AD Agent version manifest |
| ad | `get-ad-agent-config` | Get config for specific AD Agent |
| ad | `get-agent-service-credentials` | Get AD Agent service credentials |
| ad | `get-agents-and-dcs` | Get list of AD Agents and DCs |
| ad | `get-attribute-values` | Get attribute values |
| ad | `get-auth` | Get Entra authentication |
| ad | `get-configuration-value` | Get configuration value |
| ad | `get-connector-by-id` | Get the connector |
| ad | `get-connectors` | Get connectors |
| ad | `get-connectors-get` | Get loggers for all active AD Agents |
| ad | `get-current-time` | Get current time |
| ad | `get-device` | Get AD device |
| ad | `get-device-by-sid-and-domain` | Get AD device by SID and Domain |
| ad | `get-entra-users` | Entra users |
| ad | `get-group-by-sid-and-domain` | Get AD group by SID and Domain |
| ad | `get-groups-view` | Get groups view |
| ad | `get-suppressed-ip-attaches` | Get all suppressed IP attaches |
| ad | `get-user-by-sid-and-domain` | Get AD user by SID and Domain |
| ad | `get-users-count-data` | Get users count |
| ad | `get-users-logon-history` | Retrieve user logon history for a device |
| ad | `get-users-view` | Get users view |
| ad | `status` | Entra status |
| connectors | `download-export-file` | Download generated XLSX for the export task |
| connectors | `download-import-template` | Download sample XLSX import template for Custom Connector |
| connectors | `get-custom-connector-devices` | Get devices from custom connector for given layer |
| connectors | `get-export-status` | Get status of ongoing or completed export task |
| connectors | `get-status` | Get status of ongoing or completed import task |
| connectors | `read` | Get connectivity status of all configured connectors |
| connectors | `read-all-connector-configurations` | Read all connector configuration entries |
| connectors | `read-connector-configuration` | Read connector configuration by ID |
| connectors | `read-endpoints` | Get connectivity status of connector endpoints by type |
| devices | `check-ven-availability` | Check if VEN is able to accept device attach |
| devices | `feature-flag-ig` | Get current status of a feature flag |
| devices | `get-blended-enrichment-order` | Read enrichment order |
| devices | `get-configuration-by-id` | Get time-based configuration by ID |
| devices | `get-configurations` | Get time-based configurations |
| devices | `get-custom-oui-mappings` | Get custom OUI mappings |
| devices | `get-device-attribute-values` | Get device attribute values |
| devices | `get-device-attribute-values-with-display-names` | Get trustAttributes values with displayNames |
| devices | `get-device-count` | Get devices count |
| devices | `get-device-header-data` | Get devices count |
| devices | `get-enrichment-order-dto` | Read enrichment order settings entry |
| devices | `get-raw-enrichment-order` | Read raw enrichment order settings entry |
| devices | `get-users` | Get all entries (paged) |
| devices | `get-values-for-device-attribute` | Get values for device attribute |
| devices | `list-all-custom-connector-icons-base64` | List all Custom Connector icons (base64) |
| devices | `read-all-layer-instances-specification` | Read dynamic specification of all layers |
| devices | `read-all-settings` | Read all settings entries |
| devices | `read-device` | Get device by ID |
| devices | `read-history-for-device` | Read device event history by device ID |
| devices | `read-static-layer-specification` | Read static layer specification |
| devices | `search-by-name` | Search time-based configurations by name |
| devices | `search-device` | Search device by MAC |
| flows | `dump-all` | Get complete history for all devices |
| flows | `dump-latest` | Get latest data for all devices |
| flows | `get-all` | GET /api/flows/v1/refresh-info |
| flows | `get-available-ports` | Get all available ports and their names |
| flows | `get-device-data-history` | Get complete device data history |
| flows | `get-device-data-in-time-range` | Get device data history in time range |
| flows | `get-floor-data` | Get device data at or before timestamp |
| flows | `get-latest-data` | Get latest device data |
| flows | `get-latest-data-backward-compatible` | Get latest device data - backward compatible |
| flows | `get-noise-definition` | GET /api/flows/v1/noisedefinition |
| flows | `get-unique-values` | Get unique values |
| flows | `search-noise-definitions` | GET /api/flows/v1/noisedefinition/search |
| insights | `get-categories-list` | Get Categories list |
| insights | `get-policy-group-suggestions` | Get Policy Groups suggestions |
| insights | `get-policy-groups-suggestion-list` | Get all suggestions (including 'disabled' suggestions) |
| insights | `get-policy-groups-suggestion-list-get` | Get suggestions by Category |
| insights | `get-policy-suggestion-list` | Get all Policy suggestions |
| insights | `get-settings` | Get settings for Policy Suggestion |
| insights | `get-suggestions` | Get suggestion for Network Policy Suggestion |
| insights | `get-suggestions-ok-status-only` | Get suggestion for Network Policy Suggestion |
| insights | `list-network-policy-group-suggestions` | Get settings for Network Policy Suggestion |
| policy | `get-all-as-nd-json` | Get all policy sets |
| policy | `get-all-as-nd-json-get` | Get all policy group labels |
| policy | `get-all-as-nd-json-get` | Get all policy groups |
| policy | `get-all-matching-criteria` | Get match criteria labels and constant values |
| policy | `get-all-policies-as-nd-json` | Get all policies |
| policy | `get-all-policies-for-policy-group-as-nd-json` | Get all policies for given policy group (NDJSON) |
| policy | `get-all-policies-for-policy-set-as-nd-json` | Search and filter Policies in given Policy Set |
| policy | `get-all-policies-for-policy-view-as-nd-json` | Get all Policies for given Policy View |
| policy | `get-all-policy-views-as-nd-json` | Get all policy views |
| policy | `get-all-security-profiles-as-nd-json` | Get all security profiles |
| policy | `get-all-site-labels-from-all-policy-sets` | Get all site labels assigned to policy sets |
| policy | `get-count-of-all-policies-for-policy-set` | Get count of all Policies for given Policy Set |
| policy | `get-current-local-policy-groups-flag` | Get current local policy groups flag |
| policy | `get-current-multiple-policy-set-enablement-flag` | Get Security Profile Log enablement flag |
| policy | `get-device-details` | Get device details by id |
| policy | `get-enforcement-score` | Get Policy Enforcement Score With Info |
| policy | `get-enforcement-score-weight-settings` | Get settings for Policy Enforcement Score Weights |
| policy | `get-image` | Get an image |
| policy | `get-label-by-id` | Get a policy group label by ID. |
| policy | `get-local-policy-group-sites` | Get saved Site Labels with number of Local Policy Groups created for Site Label |
| policy | `get-matching-criteria-dynamic-values` | Get values for dynamic match criteria |
| policy | `get-nodes-assigned-to-policy-set` | Get virtual edge nodes assigned to Policy Set |
| policy | `get-policies-count` | Get Policies count |
| policy | `get-policies-for-security-profile` | Get policies for given security profile |
| policy | `get-policy-by-id` | Get a policy by ID |
| policy | `get-policy-group-by-id` | Get a policy group by ID |
| policy | `get-policy-group-devices` | Search and filter devices for a policy group |
| policy | `get-policy-groups-assigned-to-policy-set` | Get Policy Groups assigned to Policy Set |
| policy | `get-policy-groups-for-ven` | Get Policy Groups assigned to a VEN |
| policy | `get-policy-groups-json` | Search and filter policy groups |
| policy | `get-policy-groups-with-device-groups-for-ven` | Get Policy Groups with Device Names assigned to a VEN |
| policy | `get-policy-set-by-id` | Get a policy set by ID |
| policy | `get-state` | Get paged state of all Policy related resources. This API is using marker to paginate results. |
| policy | `get-state-get` | Get paged state of all Policy related resources. This API is using marker to paginate results. |
| policy | `get-status` | Get current status of a feature flag |
| policy | `get-template-by-id` | Get a Policy Group Template by ID |
| policy | `list-images` | List all images |
| policy | `read-policy-view` | Read a policy view by ID |
| policy | `read-security-profile` | Read a security profile by ID |
| policy | `search-templates` | Search and filter Policy Group Templates |
| system | `get-next-task-for-ve` | Allows a Virtual Edge to poll for the next highest priority task assigned to its VE Group, Site Label or to itself. The |
| system | `get-spec` | Retrieves a Spec by VE's ID. |
| system | `get-task` | Retrieves detailed information about a specific task by its ID. |
| system | `list-specs` | Retrieves a paginated list of Specs. |
| system | `list-tasks` | Retrieves a paginated list of tasks with optional filtering by VE ID, VE Group ID, Connector ID, status, priority, and o |
| topology | `get-all-cloud-controllers` | Get cloud controllers |
| topology | `get-all-distribution-zones` | Get all Distribution Zones |
| topology | `get-all-distribution-zones-get` | Get all Distribution Zones |
| topology | `get-all-flow-exporter` | Get all Flow Exporter |
| topology | `get-all-global-credentials` | Get global credentials |
| topology | `get-all-sites` | Get all Sites |
| topology | `get-all-sites-v2` | Get all Sites |
| topology | `get-all-tags` | Get all Tags used for Site Labels |
| topology | `get-all-target-sites` | Retrieves all configured deployment targets. |
| topology | `get-all-ve-ns-for-global-credentials` | Get global credentials |
| topology | `get-dashboard-count` | Get VE and VEN dashboard count |
| topology | `get-distribution-zone` | Get single Distribution Zone |
| topology | `get-flow-exporter` | Get single Flow Exporter |
| topology | `get-global-interfaces-settings` | Get global interfaces settings details |
| topology | `get-logger` | GET /api/topology/v1/virtual-edges/loggers/{loggerName} |
| topology | `get-loggers-for-all-virtual-edges` | GET /api/topology/v1/virtual-edges/loggers |
| topology | `get-manifest` | Get manifest with versions for Central VE |
| topology | `get-ports-configuration` | Get ports configuration for a VEN |
| topology | `get-single-ven` | Get single Virtual Edge Node |
| topology | `get-site` | Get single Site |
| topology | `get-site-count` | Get site count |
| topology | `get-site-count-v2` | Get site count |
| topology | `get-site-v2` | Get single Site |
| topology | `get-target-site` | Retrieves the target for a specific type. |
| topology | `get-target-types` | Retrieves all available target types with their descriptions. |
| topology | `get-topology` | Get topology for a VEN |
| topology | `get-ve-ns-overview-response` | Returns a non-paginated overview, having name and status, of Virtual Edge Nodes. |
| topology | `get-ve-variables` | Download variables for a VE |
| topology | `get-virtual-edge` | Search and filter virtual edge |
| topology | `get-virtual-edge-by-id` | Get a virtual edge by ID |
| topology | `get-virtual-edge-get` | Search and filter Virtual Edge Group |
| topology | `get-virtual-edge-group-by-id` | Get a virtual edge group by ID |
| topology | `get-virtual-edge-node-firewall-rules` | List of Firewalls and Firewall rules for given Virtual Edge Nodes with pagination |
| topology | `get-virtual-edge-nodes` | List Virtual Edge Nodes with pagination and sorting |
| topology | `is-imbalanced` | Check if Virtual Edge Group is imbalanced |

### Create operations (169 commands)

| Group | Command | Description |
|-------|---------|-------------|
| ad | `add-device-ad` | Add AD device |
| ad | `agent-status` | Set AD Agent and DC status |
| ad | `attach-device` | Attach AD device |
| ad | `attach-user` | Attach AD user |
| ad | `create-group` | Update memberOf |
| ad | `create-group-post` | Add AD group |
| ad | `create-user` | Add AD user |
| ad | `detach-device` | Detach AD device |
| ad | `detach-user` | Detach AD user |
| ad | `export` | Generate AD Agents export as CSV |
| ad | `export-users` | Generate users export as CSV |
| ad | `export-users-logon-history` | Generate users logon export as CSV |
| ad | `export-users-post` | Generate Entra users export as CSV |
| ad | `migrate-old-ad-agent-config` | Migrate old config for specific AD Agent |
| ad | `process-dc-status` | Process DcStatus |
| ad | `refresh-device` | Refresh AD device |
| ad | `refresh-user` | Refresh AD user |
| ad | `register-connector` | Register the connector |
| ad | `resync` | Resync the connector |
| ad | `save-ad-agent-config` | Save new config for specific AD Agent |
| ad | `save-logger-change` | Save log level for specific AD Agent |
| ad | `sync` | Sync Entra |
| ad | `update-agent-description` | Save AD Agent description |
| ad | `update-agent-service-credentials` | Save AD Agent service credentials |
| ad | `update-agent-to-version` | Update AD Agent to specific or latest version |
| ad | `update-auth` | Update Entra authentication |
| connectors | `async-export-devices` | Start async export of devices for custom connector as XLSX |
| connectors | `cancel-current-export` | Cancel the current ongoing export (without exportId) |
| connectors | `cancel-current-import` | Cancel the current ongoing import (without uploadId) |
| connectors | `cancel-import` | Cancel ongoing import for a custom connector |
| connectors | `create` | Create a single inventory record |
| connectors | `create-connector-configuration` | Create new connector configuration |
| connectors | `export-devices` | Export devices for custom connector as XLSX |
| connectors | `import-file` | Import XLS/XLSX file with Custom Connector data |
| connectors | `validate-connector-endpoint-configuration` | Validate connector endpoint configuration |
| devices | `attach` | Attach device by MAC or create new one if not exists |
| devices | `attached` | Attach devices by MAC or create new ones if not exists |
| devices | `bulk-create-devices` | Create new devices |
| devices | `bulk-create-devices-from-file` | Create new devices from XLSX file |
| devices | `create` | Create a new suppression entry |
| devices | `create-configuration` | Create new time-based configuration |
| devices | `create-device` | Create a new device |
| devices | `detach` | Detach device by ID |
| devices | `detach-by-mac` | Detach device by MAC and IP |
| devices | `duplicate-configuration` | Duplicate time-based configuration |
| devices | `enrich-by-id` | Enrich device by ID. |
| devices | `enrich-by-ip` | Enrich device by IP. |
| devices | `execute-bulk-refresh` | Execute a asynchronous on-demand enrichment of given devices for given sources (bulk) |
| devices | `execute-synchronous-on-demand-enrichment` | Execute a synchronous on demand enrichment of given device with a given source |
| devices | `execute-synchronous-on-demand-enrichment-post` | Execute a synchronous on demand enrichment of given device for all sources |
| devices | `export-devices` | Generate devices export as CSV |
| devices | `get-configurations-by-ids` | Get multiple time-based configurations by IDs |
| devices | `get-device-aggregate` | Get devices aggregated count |
| devices | `get-devices-view` | Get devices view |
| devices | `upsert-enrichment-order` | Update/create settings entry |
| flows | `flows-export` | Generate flows export as CSV |
| flows | `get-dash-board-summary-data` | POST /nflowsearch/api/v1/dashboardSummary |
| flows | `get-pg-data` | POST /nflowsearch/api/v1/pgdata |
| flows | `get-raw-traffic-summary` | Get traffic summary data |
| flows | `get-traffic-record` | POST /nflowsearch/api/v1/trafficRecord |
| flows | `update-noise-definition` | POST /api/flows/v1/noisedefinition |
| insights | `all-workflows-preview` | Preview all activation workflows |
| insights | `create-suggestion` | Create new suggestion |
| insights | `create-suggestions` | Create Network Policy Suggestions |
| insights | `day0workflow-preview` | Preview Policy Day 0 workflow |
| insights | `day15workflow-preview` | Preview Policy Day 15 workflow |
| insights | `day30workflow-preview` | Preview Policy Day 30 workflow |
| insights | `day7workflow-preview` | Preview Policy Day 7 workflow |
| insights | `execute-activate-workflow` | Execute activation workflow |
| insights | `execute-create-workflow` | Execute creation workflow |
| insights | `post-policy-group-suggestions-preview` | Get Policy Groups suggestions Preview |
| insights | `recreate-policy-suggestions` | Delete and Create all Policy suggestions |
| insights | `recreate-suggestions` | Delete and Create all suggestions |
| insights | `reset-policy-suggestions-to-default` | Delete and Create all default Policy Suggestions |
| insights | `reset-suggestions-to-default` | Delete and Create all default suggestions |
| insights | `reset-suggestions-to-default-post` | Delete and Create all default Network Suggestions |
| policy | `change-status` | Enable/disable feature flag |
| policy | `clone-policy-set` | Clone Policy Set |
| policy | `create-dynamic-policy-group` | Create new dynamic policy group |
| policy | `create-dynamic-policy-groups` | Bulk create of Dynamic Policy Group |
| policy | `create-image` | Create a new image |
| policy | `create-network-policy-group` | Create new network policy group |
| policy | `create-network-policy-groups` | Bulk create of Network Policy Group |
| policy | `create-policy` | Bulk create Policy |
| policy | `create-policy-group-label` | Create a new policy group label. |
| policy | `create-policy-post` | Create Policy |
| policy | `create-policy-set` | Create Policy Set |
| policy | `create-policy-view` | Create a policy view |
| policy | `create-replica-policy-set` | Create Replica Policy Set |
| policy | `create-security-profile` | Create new security profile |
| policy | `create-security-profiles` | Bulk create of Security Profiles |
| policy | `create-template` | Create new Policy Group Template |
| policy | `e-discovery-distribution-zones-state-sync` | Sends all Distribution Zones to eDiscovery.state-sync topic. |
| policy | `e-discovery-sites-state-sync` | Sends all Sites to eDiscovery.state-sync topic. |
| policy | `enable-local-policy-groups` | Enable/disable local policy groups |
| policy | `evaluate-policy` | Evaluate Policy |
| policy | `evaluate-policy-export` | Evaluate Policy and export result as CSV |
| policy | `evaluate-policy-group-for-device` | Find Policy Group, that provided Device would be classified to |
| policy | `export-policies-to-csv` | Generate policies export as CSV |
| policy | `export-policy-group-to-csv` | Generate Policy Groups export as CSV |
| policy | `export-templates` | Export Policy Group Templates to CSV |
| policy | `force-sync` | POST /api/policy/v1/state/resync |
| policy | `get-devices-current-pg-and-new-pg-after-evaluation` | Get current and expected policy groups after the devices will be unlocked |
| policy | `get-matrix` | Get matrix data |
| policy | `get-online-devices-for-distribution-zones` | Get count of online devices for distribution zones |
| policy | `get-online-devices-for-site-labels` | Get count of online devices for site labels |
| policy | `get-policy-groups-by-ids` | Search and filter policy groups by ids |
| policy | `get-policy-groups-summary` | Get Policy Groups summary |
| policy | `is-site-label-in-use` | Is Site Label used |
| policy | `lookup-dynamic` | Get Assets that are expected to Match the Dynamic Policy Group |
| policy | `lookup-dynamic-export` | Export Assets that are expected to Match the Dynamic Policy Group to CSV |
| policy | `lookup-dynamic-totals` | Count Assets that are expected to Match the Dynamic Policy Group |
| policy | `lookup-evaluation-endpoint` | Evaluation Endpoint IP lookup |
| policy | `lookup-network` | Get Assets that are expected to Match the Network Policy Group |
| policy | `lookup-network-export` | Export Assets that are expected to Match the Network Policy Group to CSV |
| policy | `partial-reorder-policy-group` | Reorder (partial) policy group |
| policy | `post-local-policy-group-site` | Save Site Label for creating Local Policy Groups |
| policy | `resync-state` | Sends details of all the VE and VENs to elisity.state-sync topic. |
| policy | `send-state-of-all-devices-to-identity-graph` | Send current state of all Devices to Identity Graph |
| policy | `send-state-of-device-to-identity-graph` | Send current state of the Devices to Identity Graph |
| policy | `validate-subnet-dynamic-policy-group` | Validate subnet for Dynamic Policy Group |
| policy | `validate-subnet-static-policy-group` | Validate subnet for Static Policy Group |
| policy | `validate-subnet-static-policy-group-post` | Bulk validate subnet for Static Policy Group |
| system | `ack-execution-of-task-post` | Acknowledge Execution of task (with result payload). |
| system | `create-task` | Creates a new task to be executed by a Virtual Edge device. |
| system | `register-specs` | Register or update OpenAPI specs for VE. |
| topology | `batch-create-or-update-multiple-rules` | Bulk create or update rules for given Palo Alto VEN and Firewall |
| topology | `bulk-create-site-labels` | Create list of sites. |
| topology | `bulk-delete-distribution-zone` | Bulk delete distribution zone. |
| topology | `bulk-delete-site` | Bulk delete site labels. |
| topology | `bulk-delete-site-v2` | Bulk delete site labels. |
| topology | `create-cloud-controller` | Create a new cloud controller. |
| topology | `create-distribution-zone` | Create list of distribution zones. |
| topology | `create-flow-exporter` | Create Flow Exporter |
| topology | `create-global-credentials` | Create a new global credentials. |
| topology | `create-or-update-bulk-target-site` | Creates or updates multiple targets in a single transaction. |
| topology | `create-or-update-multiple-rules` | Create or update rules for given Palo Alto VEN and Firewall |
| topology | `create-or-update-target-site` | Creates a new target or updates the existing target for the specified type. |
| topology | `create-site` | Create list of sites. |
| topology | `create-site-post` | Create site label. |
| topology | `create-task-list` | Create a task list, managing the status of published tasks |
| topology | `create-ven` | Create a new virtual edge node. |
| topology | `create-virtual-edge` | Create new virtual edge |
| topology | `create-virtual-edge-group` | Create new virtual edge group |
| topology | `export-distribution-zones` | Generate all distribution zones as CSV |
| topology | `export-site-labels` | Generate all site labels as CSV |
| topology | `export-virtual-edge-nodes` | Generate all virtual edge nodes as CSV |
| topology | `export-virtual-edges` | Generate all virtual edges as CSV |
| topology | `get-dashboard-metrics` | Get VE and VEN dashboard metrics |
| topology | `get-virtual-edge-by-post` | Search and filter virtual edge |
| topology | `get-virtual-edge-by-post-post` | Search and filter virtual edge |
| topology | `get-virtual-edge-nodes-by-post` | List Virtual Edge Nodes with pagination and sorting |
| topology | `heartbeat` | Register heartbeat for a VE |
| topology | `heartbeat-post` | Register heartbeat from virtual edge node. |
| topology | `metrics` | Publish operational metrics for a VE |
| topology | `metrics-post` | Publish operational metrics for a VEN |
| topology | `publish-ve-variables` | Publish variables for a VE |
| topology | `register` | Register a VE |
| topology | `register-ven` | Register virtual edge node. |
| topology | `set-logger-level` | POST /api/topology/v1/virtual-edges/loggers/{loggerName} |
| topology | `sxp-password-regenerate` | Generate all virtual edge nodes as CSV |
| topology | `topology` | Publish topology seen from a VEN |
| topology | `update-virtual-edge-post` | Regenerate OTP for existing virtual edge |
| topology | `validate-virtual-edge-bulk-delete` | Validate list of VE IDs before Virtual Edge bulk delete. |
| topology | `validate-virtual-edge-bulk-upload` | Validate XLXS file content for Virtual Edge bulk upload. |
| topology | `validate-virtual-edge-nodes-bulk-upload` | Validate XLXS file content for Virtual Edge bulk upload. |
| topology | `virtual-edge-bulk-change-group` | Virtual Edges bulk change group. |
| topology | `virtual-edge-bulk-upload` | Bulk addition of Virtual Edges from xls file. |
| topology | `virtual-edge-node-bulk-upload` | Bulk addition of Virtual Edge Nodes from xls file. |

### Update operations (68 commands)

| Group | Command | Description |
|-------|---------|-------------|
| ad | `ping` | Health check |
| ad | `put-configuration-value` | Update configuration value |
| ad | `update-device-ad` | Update AD device |
| ad | `update-group` | Update AD group |
| ad | `update-group-put` | Update AD group |
| ad | `update-user` | Update AD user |
| connectors | `update` | Update a single inventory record |
| connectors | `update-connector-configuration` | Update connector configuration by ID |
| devices | `add-device-unique-attribute-value` | Add device attribute unique value |
| devices | `apply-custom-oui-mappings` | Upload custom OUI mappings and override existing ones |
| devices | `bulk-recalculate-effective-attributes` | Recalculate effective attributes by ID |
| devices | `bulk-update-devices` | Update devices by ID |
| devices | `recalculate-attributes` | Recalculate attributes on all devices |
| devices | `update` | Update suppression entry |
| devices | `update-configuration` | Update time-based configuration |
| devices | `update-device` | Update device by ID |
| insights | `reorder-suggestion` | Reorder Suggestion |
| insights | `save-settings` | Save settings for Policy Suggestion |
| insights | `update-suggestion` | Update Suggestion |
| insights | `update-suggestion-put` | Update Network Policy Suggestion |
| policy | `enable-multiple-policy-sets` | Enable Security Profile Log |
| policy | `lock-device` | Lock Device by serviceDeviceIds |
| policy | `lock-policy-group` | Lock policy group |
| policy | `toggle-lock-bulk` | Bulk toggle lock/unlock Devices by serviceDeviceIds, creates DelayedTask for each device |
| policy | `unlock-device` | Unlock Device by serviceDeviceIds |
| policy | `unlock-policy-group` | Unlock policy group |
| policy | `update-dynamic-policy-group` | Update dynamic policy group |
| policy | `update-enforcement-score-weight-settings` | Save settings for Policy Enforcement Score Weights |
| policy | `update-image` | Update an existing image |
| policy | `update-network-policy-group` | Update network policy group |
| policy | `update-policy` | Update policy |
| policy | `update-policy-group-label` | Update an existing policy group label |
| policy | `update-policy-groups` | Bulk update of Policy Group |
| policy | `update-policy-groups-with-device-groups` | Bulk update of Policy Group with Device Group |
| policy | `update-policy-put` | Bulk update Policy |
| policy | `update-policy-set` | Update Policy Set |
| policy | `update-policy-view` | Update a policy view |
| policy | `update-security-profile` | Update a security profile |
| policy | `update-template` | Update a Policy Group Template |
| system | `ack-execution-of-task` | Acknowledge Execution of task (without result payload). |
| system | `release-execution-of-task` | Releases the task. |
| system | `update-task` | Updates task details. |
| topology | `ack-registration` | Acknowledge registration of Central VE |
| topology | `change-virtual-edge-group` | Change virtual edge group for existing virtual edge |
| topology | `decommission-virtual-edge-node` | Trigger decommission of a registered virtual edge node |
| topology | `exclude-adjacent-vens` | Exclude adjacent VENs and recreate missing ones |
| topology | `re-initialize-virtual-edge-node` | Trigger re-initialization of a unsuccessful recommission or a unsuccessful onboard. |
| topology | `rebalance-virtual-edge-group` | Rebalance Virtual Edge Group |
| topology | `recommission-virtual-edge-node` | Trigger recommission of a decommissioned virtual edge node |
| topology | `rediscover-adjacent-vens` | Rediscover adjacent VENs and recreate missing ones |
| topology | `set-version` | Set desired version in manifest of Central VE for nodeId |
| topology | `update-cloud-controller` | Update cloud controller. |
| topology | `update-distribution-zone` | Update distribution zone. |
| topology | `update-flow-exporter` | Update FlowExporter. |
| topology | `update-global-credentials` | Update global credentials. |
| topology | `update-global-interfaces-settings` | Update global interfaces settings. |
| topology | `update-interfaces-settings` | Update an interfaces settings. (deprecated) |
| topology | `update-ports-configuration` | Update ports configuration for a VEN |
| topology | `update-site` | Update site. |
| topology | `update-site-put` | Update site. |
| topology | `update-site-put` | Update site. |
| topology | `update-task-list` | Update a task list, managing the status of published tasks |
| topology | `update-task-status` | Update status of one or more tasks |
| topology | `update-ven` | Update existing virtual edge node. |
| topology | `update-virtual-edge` | Update existing virtual edge |
| topology | `update-virtual-edge-group` | Update existing virtual edge group |
| topology | `update-virtual-edge-put` | Override OTP for existing virtual edge |
| topology | `validate-virtual-edge-nodes-bulk-update` | Bulk edit Virtual Edge Nodes |

### Delete operations (43 commands)

| Group | Command | Description |
|-------|---------|-------------|
| ad | `create-group-delete` | Delete memberOf |
| ad | `delete-device-ad` | Delete AD device |
| ad | `delete-domain-data` | Delete all data related to the domain |
| ad | `delete-group` | Delete AD group |
| ad | `delete-group-delete` | Delete AD group |
| ad | `delete-user` | Delete AD user |
| ad | `unregister-connector` | Unregister the connector |
| connectors | `delete` | Delete a single inventory record |
| connectors | `delete-connector-configuration` | Delete connector configuration by ID |
| devices | `bulk-delete-devices` | Delete device |
| devices | `bulk-purge-device-layers` | Bulk purge device layers |
| devices | `delete` | Delete suppression entry |
| devices | `delete-configuration` | Delete time-based configuration |
| devices | `delete-device` | Delete device |
| devices | `delete-enrichment-order` | Delete enrichment order settings entry |
| devices | `purge-device-layer` | Purge device layer |
| insights | `delete-suggestion` | Delete Suggestion |
| insights | `delete-suggestion-delete` | Delete Network Policy Suggestions |
| policy | `delete-image` | Delete an image |
| policy | `delete-label` | Delete a policy group label by ID |
| policy | `delete-local-policy-group-site-by-id` | Remove Site Label from list of site labels for Local Policy Groups |
| policy | `delete-policy` | Delete Policy |
| policy | `delete-policy-delete` | Bulk delete Policy |
| policy | `delete-policy-group` | Delete a policy group |
| policy | `delete-policy-groups` | Bulk delete Policy Group |
| policy | `delete-policy-set` | Delete Policy Set |
| policy | `delete-policy-view` | Delete a policy view |
| policy | `delete-security-profiles` | Delete a security profile |
| policy | `delete-template` | Delete a Policy Group Template |
| system | `cancel-task` | Cancels a task by transitioning it to CANCELLED state. |
| topology | `bulk-delete-cloud-controllers` | Bulk delete cloud controllers. |
| topology | `bulk-delete-credentials` | Bulk delete credentials. |
| topology | `delete-cloud-controller` | Delete cloud controller. |
| topology | `delete-distribution-zone` | Delete distribution zone. |
| topology | `delete-flow-exporter` | Delete Flow Exporter. |
| topology | `delete-global-credentials` | Delete global credentials. |
| topology | `delete-site` | Delete site. |
| topology | `delete-site-v2` | Delete site. |
| topology | `delete-target-site` | Permanently deletes the target for the specified type. |
| topology | `delete-ven` | Delete virtual edge node. |
| topology | `delete-virtual-edge` | Delete existing virtual edge |
| topology | `delete-virtual-edge-group` | Delete existing virtual edge group |
| topology | `use-default-logger-level` | DELETE /api/topology/v1/virtual-edges/loggers/{loggerName} |

### Patch operations (2 commands)

| Group | Command | Description |
|-------|---------|-------------|
| devices | `enrich-by-id-append` | Enrich device by ID and append to existing data in layer (create layer if not exists). |
| devices | `enrich-by-ip-append` | Enrich device by IP and append to existing data in layer (create layer if not exists). |

---

## Built-in Commands

### auth

Authentication and token management.

| Command | Description |
|---------|-------------|
| `auth test` | Test CCC authentication and connectivity |
| `auth token` | Get bearer token for use in scripts or curl |
| `auth whoami` | Decode and display JWT token claims |

### config

Profile and configuration management.

| Command | Description |
|---------|-------------|
| `config set-profile NAME` | Create or update a named connection profile |
| `config use-profile NAME` | Switch the active profile |
| `config list-profiles` | List all saved profiles |
| `config show` | Show active configuration (secrets redacted) |

---

## API Command Groups

### topology (117 commands)

Manage network topology — sites, zones, VE groups, VEs, VENs, flow exporters

| Command | Method | Description |
|---------|--------|-------------|
| `ack-registration` | PUT | Acknowledge registration of Central VE |
| `batch-create-or-update-multiple-rules` | POST | Bulk create or update rules for given Palo Alto VEN and Firewall |
| `bulk-create-site-labels` | POST | Create list of sites. |
| `bulk-delete-cloud-controllers` | DELETE | Bulk delete cloud controllers. |
| `bulk-delete-credentials` | DELETE | Bulk delete credentials. |
| `bulk-delete-distribution-zone` | POST | Bulk delete distribution zone. |
| `bulk-delete-site` | POST | Bulk delete site labels. |
| `bulk-delete-site-v2` | POST | Bulk delete site labels. |
| `change-virtual-edge-group` | PUT | Change virtual edge group for existing virtual edge |
| `create-cloud-controller` | POST | Create a new cloud controller. |
| `create-distribution-zone` | POST | Create list of distribution zones. |
| `create-flow-exporter` | POST | Create Flow Exporter |
| `create-global-credentials` | POST | Create a new global credentials. |
| `create-or-update-bulk-target-site` | POST | Creates or updates multiple targets in a single transaction. |
| `create-or-update-multiple-rules` | POST | Create or update rules for given Palo Alto VEN and Firewall |
| `create-or-update-target-site` | POST | Creates a new target or updates the existing target for the specified type. |
| `create-site` | POST | Create list of sites. |
| `create-site-post` | POST | Create site label. |
| `create-task-list` | POST | Create a task list, managing the status of published tasks |
| `create-ven` | POST | Create a new virtual edge node. |
| `create-virtual-edge` | POST | Create new virtual edge |
| `create-virtual-edge-group` | POST | Create new virtual edge group |
| `decommission-virtual-edge-node` | PUT | Trigger decommission of a registered virtual edge node |
| `delete-cloud-controller` | DELETE | Delete cloud controller. |
| `delete-distribution-zone` | DELETE | Delete distribution zone. |
| `delete-flow-exporter` | DELETE | Delete Flow Exporter. |
| `delete-global-credentials` | DELETE | Delete global credentials. |
| `delete-site` | DELETE | Delete site. |
| `delete-site-v2` | DELETE | Delete site. |
| `delete-target-site` | DELETE | Permanently deletes the target for the specified type. |
| `delete-ven` | DELETE | Delete virtual edge node. |
| `delete-virtual-edge` | DELETE | Delete existing virtual edge |
| `delete-virtual-edge-group` | DELETE | Delete existing virtual edge group |
| `exclude-adjacent-vens` | PUT | Exclude adjacent VENs and recreate missing ones |
| `export-distribution-zones` | POST | Generate all distribution zones as CSV |
| `export-site-labels` | POST | Generate all site labels as CSV |
| `export-virtual-edge-nodes` | POST | Generate all virtual edge nodes as CSV |
| `export-virtual-edges` | POST | Generate all virtual edges as CSV |
| `get-all-cloud-controllers` | GET | Get cloud controllers |
| `get-all-distribution-zones` | GET | Get all Distribution Zones |
| `get-all-distribution-zones-get` | GET | Get all Distribution Zones |
| `get-all-flow-exporter` | GET | Get all Flow Exporter |
| `get-all-global-credentials` | GET | Get global credentials |
| `get-all-sites` | GET | Get all Sites |
| `get-all-sites-v2` | GET | Get all Sites |
| `get-all-tags` | GET | Get all Tags used for Site Labels |
| `get-all-target-sites` | GET | Retrieves all configured deployment targets. |
| `get-all-ve-ns-for-global-credentials` | GET | Get global credentials |
| `get-dashboard-count` | GET | Get VE and VEN dashboard count |
| `get-dashboard-metrics` | POST | Get VE and VEN dashboard metrics |
| `get-distribution-zone` | GET | Get single Distribution Zone |
| `get-flow-exporter` | GET | Get single Flow Exporter |
| `get-global-interfaces-settings` | GET | Get global interfaces settings details |
| `get-logger` | GET | GET /api/topology/v1/virtual-edges/loggers/{loggerName} |
| `get-loggers-for-all-virtual-edges` | GET | GET /api/topology/v1/virtual-edges/loggers |
| `get-manifest` | GET | Get manifest with versions for Central VE |
| `get-ports-configuration` | GET | Get ports configuration for a VEN |
| `get-single-ven` | GET | Get single Virtual Edge Node |
| `get-site` | GET | Get single Site |
| `get-site-count` | GET | Get site count |
| `get-site-count-v2` | GET | Get site count |
| `get-site-v2` | GET | Get single Site |
| `get-target-site` | GET | Retrieves the target for a specific type. |
| `get-target-types` | GET | Retrieves all available target types with their descriptions. |
| `get-topology` | GET | Get topology for a VEN |
| `get-ve-ns-overview-response` | GET | Returns a non-paginated overview, having name and status, of Virtual Edge Nodes. |
| `get-ve-variables` | GET | Download variables for a VE |
| `get-virtual-edge` | GET | Search and filter virtual edge |
| `get-virtual-edge-by-id` | GET | Get a virtual edge by ID |
| `get-virtual-edge-by-post` | POST | Search and filter virtual edge |
| `get-virtual-edge-by-post-post` | POST | Search and filter virtual edge |
| `get-virtual-edge-get` | GET | Search and filter Virtual Edge Group |
| `get-virtual-edge-group-by-id` | GET | Get a virtual edge group by ID |
| `get-virtual-edge-node-firewall-rules` | GET | List of Firewalls and Firewall rules for given Virtual Edge Nodes with pagination |
| `get-virtual-edge-nodes` | GET | List Virtual Edge Nodes with pagination and sorting |
| `get-virtual-edge-nodes-by-post` | POST | List Virtual Edge Nodes with pagination and sorting |
| `heartbeat` | POST | Register heartbeat for a VE |
| `heartbeat-post` | POST | Register heartbeat from virtual edge node. |
| `is-imbalanced` | GET | Check if Virtual Edge Group is imbalanced |
| `metrics` | POST | Publish operational metrics for a VE |
| `metrics-post` | POST | Publish operational metrics for a VEN |
| `publish-ve-variables` | POST | Publish variables for a VE |
| `re-initialize-virtual-edge-node` | PUT | Trigger re-initialization of a unsuccessful recommission or a unsuccessful onboard. |
| `rebalance-virtual-edge-group` | PUT | Rebalance Virtual Edge Group |
| `recommission-virtual-edge-node` | PUT | Trigger recommission of a decommissioned virtual edge node |
| `rediscover-adjacent-vens` | PUT | Rediscover adjacent VENs and recreate missing ones |
| `register` | POST | Register a VE |
| `register-ven` | POST | Register virtual edge node. |
| `set-logger-level` | POST | POST /api/topology/v1/virtual-edges/loggers/{loggerName} |
| `set-version` | PUT | Set desired version in manifest of Central VE for nodeId |
| `sxp-password-regenerate` | POST | Generate all virtual edge nodes as CSV |
| `topology` | POST | Publish topology seen from a VEN |
| `update-cloud-controller` | PUT | Update cloud controller. |
| `update-distribution-zone` | PUT | Update distribution zone. |
| `update-flow-exporter` | PUT | Update FlowExporter. |
| `update-global-credentials` | PUT | Update global credentials. |
| `update-global-interfaces-settings` | PUT | Update global interfaces settings. |
| `update-interfaces-settings` | PUT | Update an interfaces settings. (deprecated) |
| `update-ports-configuration` | PUT | Update ports configuration for a VEN |
| `update-site` | PUT | Update site. |
| `update-site-put` | PUT | Update site. |
| `update-site-put` | PUT | Update site. |
| `update-task-list` | PUT | Update a task list, managing the status of published tasks |
| `update-task-status` | PUT | Update status of one or more tasks |
| `update-ven` | PUT | Update existing virtual edge node. |
| `update-virtual-edge` | PUT | Update existing virtual edge |
| `update-virtual-edge-group` | PUT | Update existing virtual edge group |
| `update-virtual-edge-post` | POST | Regenerate OTP for existing virtual edge |
| `update-virtual-edge-put` | PUT | Override OTP for existing virtual edge |
| `use-default-logger-level` | DELETE | DELETE /api/topology/v1/virtual-edges/loggers/{loggerName} |
| `validate-virtual-edge-bulk-delete` | POST | Validate list of VE IDs before Virtual Edge bulk delete. |
| `validate-virtual-edge-bulk-upload` | POST | Validate XLXS file content for Virtual Edge bulk upload. |
| `validate-virtual-edge-nodes-bulk-update` | PUT | Bulk edit Virtual Edge Nodes |
| `validate-virtual-edge-nodes-bulk-upload` | POST | Validate XLXS file content for Virtual Edge bulk upload. |
| `virtual-edge-bulk-change-group` | POST | Virtual Edges bulk change group. |
| `virtual-edge-bulk-upload` | POST | Bulk addition of Virtual Edges from xls file. |
| `virtual-edge-node-bulk-upload` | POST | Bulk addition of Virtual Edge Nodes from xls file. |

### policy (117 commands)

Manage microsegmentation policies — policy sets, policies, groups, security profiles

| Command | Method | Description |
|---------|--------|-------------|
| `change-status` | POST | Enable/disable feature flag |
| `clone-policy-set` | POST | Clone Policy Set |
| `create-dynamic-policy-group` | POST | Create new dynamic policy group |
| `create-dynamic-policy-groups` | POST | Bulk create of Dynamic Policy Group |
| `create-image` | POST | Create a new image |
| `create-network-policy-group` | POST | Create new network policy group |
| `create-network-policy-groups` | POST | Bulk create of Network Policy Group |
| `create-policy` | POST | Bulk create Policy |
| `create-policy-group-label` | POST | Create a new policy group label. |
| `create-policy-post` | POST | Create Policy |
| `create-policy-set` | POST | Create Policy Set |
| `create-policy-view` | POST | Create a policy view |
| `create-replica-policy-set` | POST | Create Replica Policy Set |
| `create-security-profile` | POST | Create new security profile |
| `create-security-profiles` | POST | Bulk create of Security Profiles |
| `create-template` | POST | Create new Policy Group Template |
| `delete-image` | DELETE | Delete an image |
| `delete-label` | DELETE | Delete a policy group label by ID |
| `delete-local-policy-group-site-by-id` | DELETE | Remove Site Label from list of site labels for Local Policy Groups |
| `delete-policy` | DELETE | Delete Policy |
| `delete-policy-delete` | DELETE | Bulk delete Policy |
| `delete-policy-group` | DELETE | Delete a policy group |
| `delete-policy-groups` | DELETE | Bulk delete Policy Group |
| `delete-policy-set` | DELETE | Delete Policy Set |
| `delete-policy-view` | DELETE | Delete a policy view |
| `delete-security-profiles` | DELETE | Delete a security profile |
| `delete-template` | DELETE | Delete a Policy Group Template |
| `e-discovery-distribution-zones-state-sync` | POST | Sends all Distribution Zones to eDiscovery.state-sync topic. |
| `e-discovery-sites-state-sync` | POST | Sends all Sites to eDiscovery.state-sync topic. |
| `enable-local-policy-groups` | POST | Enable/disable local policy groups |
| `enable-multiple-policy-sets` | PUT | Enable Security Profile Log |
| `evaluate-policy` | POST | Evaluate Policy |
| `evaluate-policy-export` | POST | Evaluate Policy and export result as CSV |
| `evaluate-policy-group-for-device` | POST | Find Policy Group, that provided Device would be classified to |
| `export-policies-to-csv` | POST | Generate policies export as CSV |
| `export-policy-group-to-csv` | POST | Generate Policy Groups export as CSV |
| `export-templates` | POST | Export Policy Group Templates to CSV |
| `force-sync` | POST | POST /api/policy/v1/state/resync |
| `get-all-as-nd-json` | GET | Get all policy sets |
| `get-all-as-nd-json-get` | GET | Get all policy group labels |
| `get-all-as-nd-json-get` | GET | Get all policy groups |
| `get-all-matching-criteria` | GET | Get match criteria labels and constant values |
| `get-all-policies-as-nd-json` | GET | Get all policies |
| `get-all-policies-for-policy-group-as-nd-json` | GET | Get all policies for given policy group (NDJSON) |
| `get-all-policies-for-policy-set-as-nd-json` | GET | Search and filter Policies in given Policy Set |
| `get-all-policies-for-policy-view-as-nd-json` | GET | Get all Policies for given Policy View |
| `get-all-policy-views-as-nd-json` | GET | Get all policy views |
| `get-all-security-profiles-as-nd-json` | GET | Get all security profiles |
| `get-all-site-labels-from-all-policy-sets` | GET | Get all site labels assigned to policy sets |
| `get-count-of-all-policies-for-policy-set` | GET | Get count of all Policies for given Policy Set |
| `get-current-local-policy-groups-flag` | GET | Get current local policy groups flag |
| `get-current-multiple-policy-set-enablement-flag` | GET | Get Security Profile Log enablement flag |
| `get-device-details` | GET | Get device details by id |
| `get-devices-current-pg-and-new-pg-after-evaluation` | POST | Get current and expected policy groups after the devices will be unlocked |
| `get-enforcement-score` | GET | Get Policy Enforcement Score With Info |
| `get-enforcement-score-weight-settings` | GET | Get settings for Policy Enforcement Score Weights |
| `get-image` | GET | Get an image |
| `get-label-by-id` | GET | Get a policy group label by ID. |
| `get-local-policy-group-sites` | GET | Get saved Site Labels with number of Local Policy Groups created for Site Label |
| `get-matching-criteria-dynamic-values` | GET | Get values for dynamic match criteria |
| `get-matrix` | POST | Get matrix data |
| `get-nodes-assigned-to-policy-set` | GET | Get virtual edge nodes assigned to Policy Set |
| `get-online-devices-for-distribution-zones` | POST | Get count of online devices for distribution zones |
| `get-online-devices-for-site-labels` | POST | Get count of online devices for site labels |
| `get-policies-count` | GET | Get Policies count |
| `get-policies-for-security-profile` | GET | Get policies for given security profile |
| `get-policy-by-id` | GET | Get a policy by ID |
| `get-policy-group-by-id` | GET | Get a policy group by ID |
| `get-policy-group-devices` | GET | Search and filter devices for a policy group |
| `get-policy-groups-assigned-to-policy-set` | GET | Get Policy Groups assigned to Policy Set |
| `get-policy-groups-by-ids` | POST | Search and filter policy groups by ids |
| `get-policy-groups-for-ven` | GET | Get Policy Groups assigned to a VEN |
| `get-policy-groups-json` | GET | Search and filter policy groups |
| `get-policy-groups-summary` | POST | Get Policy Groups summary |
| `get-policy-groups-with-device-groups-for-ven` | GET | Get Policy Groups with Device Names assigned to a VEN |
| `get-policy-set-by-id` | GET | Get a policy set by ID |
| `get-state` | GET | Get paged state of all Policy related resources. This API is using marker to paginate results. |
| `get-state-get` | GET | Get paged state of all Policy related resources. This API is using marker to paginate results. |
| `get-status` | GET | Get current status of a feature flag |
| `get-template-by-id` | GET | Get a Policy Group Template by ID |
| `is-site-label-in-use` | POST | Is Site Label used |
| `list-images` | GET | List all images |
| `lock-device` | PUT | Lock Device by serviceDeviceIds |
| `lock-policy-group` | PUT | Lock policy group |
| `lookup-dynamic` | POST | Get Assets that are expected to Match the Dynamic Policy Group |
| `lookup-dynamic-export` | POST | Export Assets that are expected to Match the Dynamic Policy Group to CSV |
| `lookup-dynamic-totals` | POST | Count Assets that are expected to Match the Dynamic Policy Group |
| `lookup-evaluation-endpoint` | POST | Evaluation Endpoint IP lookup |
| `lookup-network` | POST | Get Assets that are expected to Match the Network Policy Group |
| `lookup-network-export` | POST | Export Assets that are expected to Match the Network Policy Group to CSV |
| `partial-reorder-policy-group` | POST | Reorder (partial) policy group |
| `post-local-policy-group-site` | POST | Save Site Label for creating Local Policy Groups |
| `read-policy-view` | GET | Read a policy view by ID |
| `read-security-profile` | GET | Read a security profile by ID |
| `resync-state` | POST | Sends details of all the VE and VENs to elisity.state-sync topic. |
| `search-templates` | GET | Search and filter Policy Group Templates |
| `send-state-of-all-devices-to-identity-graph` | POST | Send current state of all Devices to Identity Graph |
| `send-state-of-device-to-identity-graph` | POST | Send current state of the Devices to Identity Graph |
| `toggle-lock-bulk` | PUT | Bulk toggle lock/unlock Devices by serviceDeviceIds, creates DelayedTask for each device |
| `unlock-device` | PUT | Unlock Device by serviceDeviceIds |
| `unlock-policy-group` | PUT | Unlock policy group |
| `update-dynamic-policy-group` | PUT | Update dynamic policy group |
| `update-enforcement-score-weight-settings` | PUT | Save settings for Policy Enforcement Score Weights |
| `update-image` | PUT | Update an existing image |
| `update-network-policy-group` | PUT | Update network policy group |
| `update-policy` | PUT | Update policy |
| `update-policy-group-label` | PUT | Update an existing policy group label |
| `update-policy-groups` | PUT | Bulk update of Policy Group |
| `update-policy-groups-with-device-groups` | PUT | Bulk update of Policy Group with Device Group |
| `update-policy-put` | PUT | Bulk update Policy |
| `update-policy-set` | PUT | Update Policy Set |
| `update-policy-view` | PUT | Update a policy view |
| `update-security-profile` | PUT | Update a security profile |
| `update-template` | PUT | Update a Policy Group Template |
| `validate-subnet-dynamic-policy-group` | POST | Validate subnet for Dynamic Policy Group |
| `validate-subnet-static-policy-group` | POST | Validate subnet for Static Policy Group |
| `validate-subnet-static-policy-group-post` | POST | Bulk validate subnet for Static Policy Group |

### devices (59 commands)

Device identity and enrichment — CRUD, bulk, attach, enrich, events

| Command | Method | Description |
|---------|--------|-------------|
| `add-device-unique-attribute-value` | PUT | Add device attribute unique value |
| `apply-custom-oui-mappings` | PUT | Upload custom OUI mappings and override existing ones |
| `attach` | POST | Attach device by MAC or create new one if not exists |
| `attached` | POST | Attach devices by MAC or create new ones if not exists |
| `bulk-create-devices` | POST | Create new devices |
| `bulk-create-devices-from-file` | POST | Create new devices from XLSX file |
| `bulk-delete-devices` | DELETE | Delete device |
| `bulk-purge-device-layers` | DELETE | Bulk purge device layers |
| `bulk-recalculate-effective-attributes` | PUT | Recalculate effective attributes by ID |
| `bulk-update-devices` | PUT | Update devices by ID |
| `check-ven-availability` | GET | Check if VEN is able to accept device attach |
| `create` | POST | Create a new suppression entry |
| `create-configuration` | POST | Create new time-based configuration |
| `create-device` | POST | Create a new device |
| `delete` | DELETE | Delete suppression entry |
| `delete-configuration` | DELETE | Delete time-based configuration |
| `delete-device` | DELETE | Delete device |
| `delete-enrichment-order` | DELETE | Delete enrichment order settings entry |
| `detach` | POST | Detach device by ID |
| `detach-by-mac` | POST | Detach device by MAC and IP |
| `duplicate-configuration` | POST | Duplicate time-based configuration |
| `enrich-by-id` | POST | Enrich device by ID. |
| `enrich-by-id-append` | PATCH | Enrich device by ID and append to existing data in layer (create layer if not exists). |
| `enrich-by-ip` | POST | Enrich device by IP. |
| `enrich-by-ip-append` | PATCH | Enrich device by IP and append to existing data in layer (create layer if not exists). |
| `execute-bulk-refresh` | POST | Execute a asynchronous on-demand enrichment of given devices for given sources (bulk) |
| `execute-synchronous-on-demand-enrichment` | POST | Execute a synchronous on demand enrichment of given device with a given source |
| `execute-synchronous-on-demand-enrichment-post` | POST | Execute a synchronous on demand enrichment of given device for all sources |
| `export-devices` | POST | Generate devices export as CSV |
| `feature-flag-ig` | GET | Get current status of a feature flag |
| `get-blended-enrichment-order` | GET | Read enrichment order |
| `get-configuration-by-id` | GET | Get time-based configuration by ID |
| `get-configurations` | GET | Get time-based configurations |
| `get-configurations-by-ids` | POST | Get multiple time-based configurations by IDs |
| `get-custom-oui-mappings` | GET | Get custom OUI mappings |
| `get-device-aggregate` | POST | Get devices aggregated count |
| `get-device-attribute-values` | GET | Get device attribute values |
| `get-device-attribute-values-with-display-names` | GET | Get trustAttributes values with displayNames |
| `get-device-count` | GET | Get devices count |
| `get-device-header-data` | GET | Get devices count |
| `get-devices-view` | POST | Get devices view |
| `get-enrichment-order-dto` | GET | Read enrichment order settings entry |
| `get-raw-enrichment-order` | GET | Read raw enrichment order settings entry |
| `get-users` | GET | Get all entries (paged) |
| `get-values-for-device-attribute` | GET | Get values for device attribute |
| `list-all-custom-connector-icons-base64` | GET | List all Custom Connector icons (base64) |
| `purge-device-layer` | DELETE | Purge device layer |
| `read-all-layer-instances-specification` | GET | Read dynamic specification of all layers |
| `read-all-settings` | GET | Read all settings entries |
| `read-device` | GET | Get device by ID |
| `read-history-for-device` | GET | Read device event history by device ID |
| `read-static-layer-specification` | GET | Read static layer specification |
| `recalculate-attributes` | PUT | Recalculate attributes on all devices |
| `search-by-name` | GET | Search time-based configurations by name |
| `search-device` | GET | Search device by MAC |
| `update` | PUT | Update suppression entry |
| `update-configuration` | PUT | Update time-based configuration |
| `update-device` | PUT | Update device by ID |
| `upsert-enrichment-order` | POST | Update/create settings entry |

### connectors (22 commands)

Connector management — custom connectors, configurations, connectivity

| Command | Method | Description |
|---------|--------|-------------|
| `async-export-devices` | POST | Start async export of devices for custom connector as XLSX |
| `cancel-current-export` | POST | Cancel the current ongoing export (without exportId) |
| `cancel-current-import` | POST | Cancel the current ongoing import (without uploadId) |
| `cancel-import` | POST | Cancel ongoing import for a custom connector |
| `create` | POST | Create a single inventory record |
| `create-connector-configuration` | POST | Create new connector configuration |
| `delete` | DELETE | Delete a single inventory record |
| `delete-connector-configuration` | DELETE | Delete connector configuration by ID |
| `download-export-file` | GET | Download generated XLSX for the export task |
| `download-import-template` | GET | Download sample XLSX import template for Custom Connector |
| `export-devices` | POST | Export devices for custom connector as XLSX |
| `get-custom-connector-devices` | GET | Get devices from custom connector for given layer |
| `get-export-status` | GET | Get status of ongoing or completed export task |
| `get-status` | GET | Get status of ongoing or completed import task |
| `import-file` | POST | Import XLS/XLSX file with Custom Connector data |
| `read` | GET | Get connectivity status of all configured connectors |
| `read-all-connector-configurations` | GET | Read all connector configuration entries |
| `read-connector-configuration` | GET | Read connector configuration by ID |
| `read-endpoints` | GET | Get connectivity status of connector endpoints by type |
| `update` | PUT | Update a single inventory record |
| `update-connector-configuration` | PUT | Update connector configuration by ID |
| `validate-connector-endpoint-configuration` | POST | Validate connector endpoint configuration |

### ad (61 commands)

Active Directory / Entra ID integration — connectors, users, groups, agents

| Command | Method | Description |
|---------|--------|-------------|
| `add-device-ad` | POST | Add AD device |
| `agent-manifest` | GET | Get AD Agent version manifest |
| `agent-status` | POST | Set AD Agent and DC status |
| `attach-device` | POST | Attach AD device |
| `attach-user` | POST | Attach AD user |
| `create-group` | POST | Update memberOf |
| `create-group-delete` | DELETE | Delete memberOf |
| `create-group-post` | POST | Add AD group |
| `create-user` | POST | Add AD user |
| `delete-device-ad` | DELETE | Delete AD device |
| `delete-domain-data` | DELETE | Delete all data related to the domain |
| `delete-group` | DELETE | Delete AD group |
| `delete-group-delete` | DELETE | Delete AD group |
| `delete-user` | DELETE | Delete AD user |
| `detach-device` | POST | Detach AD device |
| `detach-user` | POST | Detach AD user |
| `export` | POST | Generate AD Agents export as CSV |
| `export-users` | POST | Generate users export as CSV |
| `export-users-logon-history` | POST | Generate users logon export as CSV |
| `export-users-post` | POST | Generate Entra users export as CSV |
| `get-ad-agent-config` | GET | Get config for specific AD Agent |
| `get-agent-service-credentials` | GET | Get AD Agent service credentials |
| `get-agents-and-dcs` | GET | Get list of AD Agents and DCs |
| `get-attribute-values` | GET | Get attribute values |
| `get-auth` | GET | Get Entra authentication |
| `get-configuration-value` | GET | Get configuration value |
| `get-connector-by-id` | GET | Get the connector |
| `get-connectors` | GET | Get connectors |
| `get-connectors-get` | GET | Get loggers for all active AD Agents |
| `get-current-time` | GET | Get current time |
| `get-device` | GET | Get AD device |
| `get-device-by-sid-and-domain` | GET | Get AD device by SID and Domain |
| `get-entra-users` | GET | Entra users |
| `get-group-by-sid-and-domain` | GET | Get AD group by SID and Domain |
| `get-groups-view` | GET | Get groups view |
| `get-suppressed-ip-attaches` | GET | Get all suppressed IP attaches |
| `get-user-by-sid-and-domain` | GET | Get AD user by SID and Domain |
| `get-users-count-data` | GET | Get users count |
| `get-users-logon-history` | GET | Retrieve user logon history for a device |
| `get-users-view` | GET | Get users view |
| `migrate-old-ad-agent-config` | POST | Migrate old config for specific AD Agent |
| `ping` | PUT | Health check |
| `process-dc-status` | POST | Process DcStatus |
| `put-configuration-value` | PUT | Update configuration value |
| `refresh-device` | POST | Refresh AD device |
| `refresh-user` | POST | Refresh AD user |
| `register-connector` | POST | Register the connector |
| `resync` | POST | Resync the connector |
| `save-ad-agent-config` | POST | Save new config for specific AD Agent |
| `save-logger-change` | POST | Save log level for specific AD Agent |
| `status` | GET | Entra status |
| `sync` | POST | Sync Entra |
| `unregister-connector` | DELETE | Unregister the connector |
| `update-agent-description` | POST | Save AD Agent description |
| `update-agent-service-credentials` | POST | Save AD Agent service credentials |
| `update-agent-to-version` | POST | Update AD Agent to specific or latest version |
| `update-auth` | POST | Update Entra authentication |
| `update-device-ad` | PUT | Update AD device |
| `update-group` | PUT | Update AD group |
| `update-group-put` | PUT | Update AD group |
| `update-user` | PUT | Update AD user |

### flows (18 commands)

Traffic analytics — device state, flow search, noise definitions

| Command | Method | Description |
|---------|--------|-------------|
| `dump-all` | GET | Get complete history for all devices |
| `dump-latest` | GET | Get latest data for all devices |
| `flows-export` | POST | Generate flows export as CSV |
| `get-all` | GET | GET /api/flows/v1/refresh-info |
| `get-available-ports` | GET | Get all available ports and their names |
| `get-dash-board-summary-data` | POST | POST /nflowsearch/api/v1/dashboardSummary |
| `get-device-data-history` | GET | Get complete device data history |
| `get-device-data-in-time-range` | GET | Get device data history in time range |
| `get-floor-data` | GET | Get device data at or before timestamp |
| `get-latest-data` | GET | Get latest device data |
| `get-latest-data-backward-compatible` | GET | Get latest device data - backward compatible |
| `get-noise-definition` | GET | GET /api/flows/v1/noisedefinition |
| `get-pg-data` | POST | POST /nflowsearch/api/v1/pgdata |
| `get-raw-traffic-summary` | POST | Get traffic summary data |
| `get-traffic-record` | POST | POST /nflowsearch/api/v1/trafficRecord |
| `get-unique-values` | GET | Get unique values |
| `search-noise-definitions` | GET | GET /api/flows/v1/noisedefinition/search |
| `update-noise-definition` | POST | POST /api/flows/v1/noisedefinition |

### insights (30 commands)

Policy insights and suggestions — dynamic/network group recommendations

| Command | Method | Description |
|---------|--------|-------------|
| `all-workflows-preview` | POST | Preview all activation workflows |
| `create-suggestion` | POST | Create new suggestion |
| `create-suggestions` | POST | Create Network Policy Suggestions |
| `day0workflow-preview` | POST | Preview Policy Day 0 workflow |
| `day15workflow-preview` | POST | Preview Policy Day 15 workflow |
| `day30workflow-preview` | POST | Preview Policy Day 30 workflow |
| `day7workflow-preview` | POST | Preview Policy Day 7 workflow |
| `delete-suggestion` | DELETE | Delete Suggestion |
| `delete-suggestion-delete` | DELETE | Delete Network Policy Suggestions |
| `execute-activate-workflow` | POST | Execute activation workflow |
| `execute-create-workflow` | POST | Execute creation workflow |
| `get-categories-list` | GET | Get Categories list |
| `get-policy-group-suggestions` | GET | Get Policy Groups suggestions |
| `get-policy-groups-suggestion-list` | GET | Get all suggestions (including 'disabled' suggestions) |
| `get-policy-groups-suggestion-list-get` | GET | Get suggestions by Category |
| `get-policy-suggestion-list` | GET | Get all Policy suggestions |
| `get-settings` | GET | Get settings for Policy Suggestion |
| `get-suggestions` | GET | Get suggestion for Network Policy Suggestion |
| `get-suggestions-ok-status-only` | GET | Get suggestion for Network Policy Suggestion |
| `list-network-policy-group-suggestions` | GET | Get settings for Network Policy Suggestion |
| `post-policy-group-suggestions-preview` | POST | Get Policy Groups suggestions Preview |
| `recreate-policy-suggestions` | POST | Delete and Create all Policy suggestions |
| `recreate-suggestions` | POST | Delete and Create all suggestions |
| `reorder-suggestion` | PUT | Reorder Suggestion |
| `reset-policy-suggestions-to-default` | POST | Delete and Create all default Policy Suggestions |
| `reset-suggestions-to-default` | POST | Delete and Create all default suggestions |
| `reset-suggestions-to-default-post` | POST | Delete and Create all default Network Suggestions |
| `save-settings` | PUT | Save settings for Policy Suggestion |
| `update-suggestion` | PUT | Update Suggestion |
| `update-suggestion-put` | PUT | Update Network Policy Suggestion |

### system (12 commands)

System operations — tasks, specs, state sync

| Command | Method | Description |
|---------|--------|-------------|
| `ack-execution-of-task` | PUT | Acknowledge Execution of task (without result payload). |
| `ack-execution-of-task-post` | POST | Acknowledge Execution of task (with result payload). |
| `cancel-task` | DELETE | Cancels a task by transitioning it to CANCELLED state. |
| `create-task` | POST | Creates a new task to be executed by a Virtual Edge device. |
| `get-next-task-for-ve` | GET | Allows a Virtual Edge to poll for the next highest priority task assigned to its VE Group, Site Label or to itself. The |
| `get-spec` | GET | Retrieves a Spec by VE's ID. |
| `get-task` | GET | Retrieves detailed information about a specific task by its ID. |
| `list-specs` | GET | Retrieves a paginated list of Specs. |
| `list-tasks` | GET | Retrieves a paginated list of tasks with optional filtering by VE ID, VE Group ID, Connector ID, status, priority, and o |
| `register-specs` | POST | Register or update OpenAPI specs for VE. |
| `release-execution-of-task` | PUT | Releases the task. |
| `update-task` | PUT | Updates task details. |

---

## Global Options

All API commands support these hidden flags:

| Flag | Description |
|------|-------------|
| `--format`, `-f` | Output format override: `json`, `table`, `yaml`, `csv` |
| `--query`, `-q` | JMESPath query to filter/reshape output |

Mutating commands (`POST`, `PUT`, `PATCH`) accept:

| Flag | Description |
|------|-------------|
| `--body JSON` | Request body as inline JSON string |
| `--body-file PATH` | Read request body from a JSON file |

Destructive commands (`DELETE`) require `--confirm` to execute.

