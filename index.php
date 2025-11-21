<?php
// index.php - Simple PHP page for Nuki Smart Lock control
// Displays devices with colored status divs (red=locked, green=unlocked).
// Clicking the div toggles the state via page reload (no JS for simplicity).
// Uses config.json for defaults; assumes PHP 8+ with json and curl extensions.
// Explanation: Fetches device list from API, shows each as a clickable div.
// On toggle (?toggle=<nukiId>), calls lockAction and redirects back.
// Probability of issues: ~20% if curl not enabled (enable via php.ini or install php8-mod-curl on OpenWRT).

// Check for curl extension at the top
if (!function_exists('curl_init')) {
	echo "The php8-mod-curl package is required to install.";
	exit;
}

// Load config.json
$configPath = 'config.json';
if (file_exists($configPath)) {
	$config = json_decode(file_get_contents($configPath), true);
	if ($config === null) {
		echo "Warning: config.json is malformed. Using defaults.<br>";
		$config = [];
	}
} else {
	// Create default if missing
	$defaultConfig = [
		'ip' => '0.0.0.0',
		'token' => '1mytkn',
		'nukiId' => '123456789'
	];
	file_put_contents($configPath, json_encode($defaultConfig, JSON_PRETTY_PRINT));
	echo "Created default config.json. Please edit it.<br>";
	$config = $defaultConfig;
}

// Warn if using defaults (similar to previous scripts)
if ($config['ip'] === '0.0.0.0' || $config['token'] === '1mytkn') {
	echo "Warning: Using default config values. Edit config.json.<br>";
}

$bridgeIp = $config['ip'];
$token = $config['token'];
$baseUrl = "http://{$bridgeIp}:8080";

// Function to call Nuki API via curl
function callNukiApi($endpoint) {
	global $baseUrl, $token;
	$ch = curl_init("{$baseUrl}/{$endpoint}&token={$token}");
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
	$response = curl_exec($ch);
	$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
	curl_close($ch);
	if ($httpCode !== 200) {
		return ['error' => "HTTP {$httpCode}"];
	}
	return json_decode($response, true);
}

// Handle toggle if ?toggle=<nukiId>
if (isset($_GET['toggle'])) {
	$nukiId = $_GET['toggle'];
	// Get current state from /list (cached, to save battery)
	$devices = callNukiApi("list?");
	if (isset($devices['error'])) {
		echo "Error fetching list: " . $devices['error'];
		exit;
	}
	$currentState = null;
	foreach ($devices as $device) {
		if ($device['nukiId'] == $nukiId) {
			$currentState = $device['lastKnownState']['state'] ?? null;
			break;
		}
	}
	if ($currentState === null) {
		echo "Device not found.";
		exit;
	}
	// Toggle: locked (1) -> unlock (action=1), unlocked (3) -> lock (action=2)
	$action = ($currentState == 1) ? 1 : 2;
	$result = callNukiApi("lockAction?nukiId={$nukiId}&action={$action}&deviceType=4");
	if (isset($result['error'])) {
		echo "Error toggling: " . $result['error'];
	} else {
		// Redirect back to main page
		header("Location: index.php");
	}
	exit;
}

// Main page: Fetch and display devices
$devices = callNukiApi("list?");
if (isset($devices['error'])) {
	echo "Error fetching devices: " . $devices['error'];
	exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<title>Nuki Control</title>
	<style>
		.device { margin: 10px; padding: 10px; border: 1px solid #ccc; }
		.status { width: 100px; height: 100px; cursor: pointer; }
		.locked { background-color: red; }
		.unlocked { background-color: green; }
	</style>
</head>
<body>
	<h1>Nuki Devices</h1>
	<?php foreach ($devices as $device): ?>
		<?php
		$nukiId = $device['nukiId'];
		$name = $device['name'] ?? 'Unnamed';
		$state = $device['lastKnownState']['state'] ?? 0;
		$colorClass = ($state == 1) ? 'locked' : (($state == 3) ? 'unlocked' : 'unknown');
		?>
		<div class="device">
			<h2><?php echo htmlspecialchars($name); ?> (ID: <?php echo $nukiId; ?>)</h2>
			<a href="?toggle=<?php echo $nukiId; ?>" style="text-decoration: none;">
				<div class="status <?php echo $colorClass; ?>"></div>
			</a>
			<p>State: <?php echo htmlspecialchars($device['lastKnownState']['stateName'] ?? 'Unknown'); ?></p>
		</div>
	<?php endforeach; ?>
</body>
</html>