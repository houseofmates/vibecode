// Workspace layering system - machine ID constants for consistency
const MACHINES = [
  { id: 'ubuntu', label: 'ubuntu home', hostname: window.MEMSTER_HOST || window.UBUNTU_IP || '127.0.0.1', default_workspace: window.DEFAULT_HOME || '~', color: 'blue' },
  { id: 'popos', label: 'pop! os home', hostname: window.MEMSTER_HOST_LEGACY || window.POPOS_IP || '127.0.0.1', default_workspace: window.DEFAULT_HOME || '~', color: 'yellow' }
];

function getMachines() { return MACHINES; }

console.log('workspace layering loaded');
