// Chart.js default configuration
Chart.defaults.color = '#a0a0a0';
Chart.defaults.borderColor = '#2d3748';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

const COLORS = {
    accent: '#f59e0b',
    purple: '#8b5cf6',
    green: '#10b981',
    red: '#ef4444',
    cyan: '#06b6d4',
    pink: '#ec4899',
    blue: '#3b82f6',
    orange: '#f97316',
};

const CHART_COLORS = [
    COLORS.accent,
    COLORS.purple,
    COLORS.green,
    COLORS.cyan,
    COLORS.pink,
    COLORS.blue,
    COLORS.orange,
    COLORS.red,
];

// Store chart instances for destruction on filter change
const chartInstances = {};

// Store original unfiltered stats
let originalStats = null;

function formatNumber(num) {
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
    if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
    return num.toString();
}

function formatDuration(ms) {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
}

function formatDurationSeconds(ms) {
    if (ms >= 60000) {
        const minutes = Math.floor(ms / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        return `${minutes}m ${seconds}s`;
    }
    return `${(ms / 1000).toFixed(1)}s`;
}

function formatCurrency(value) {
    if (value >= 1000) return `$${(value / 1000).toFixed(2)}K`;
    if (value >= 1) return `$${value.toFixed(2)}`;
    return `$${value.toFixed(3)}`;
}

function formatPercent(value) {
    return `${(value * 100).toFixed(1)}%`;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getModelDisplayName(model) {
    if (model.includes('opus')) return 'Opus';
    if (model.includes('sonnet')) return 'Sonnet';
    if (model.includes('haiku')) return 'Haiku';
    return model.split('-')[1] || model;
}

function getMcpServerName(toolName) {
    const parts = toolName.split('__');
    return parts.length >= 2 ? parts[1] : toolName;
}

function getMcpToolName(toolName) {
    const parts = toolName.split('__');
    return parts.length >= 3 ? parts[2] : toolName;
}

function showEmptyState(container, title, message) {
    container.innerHTML = `<h2>${title}</h2><p class="empty">${message}</p>`;
}

function destroyChart(chartId) {
    if (chartInstances[chartId]) {
        chartInstances[chartId].destroy();
        delete chartInstances[chartId];
    }
}

function filterStatsByDateRange(stats, startDate, endDate) {
    if (!startDate && !endDate) {
        return stats;
    }

    const start = startDate ? new Date(startDate) : null;
    const end = endDate ? new Date(endDate) : null;

    const filterByDate = (dateStr) => {
        if (!dateStr) return true;
        const date = new Date(dateStr);
        if (start && date < start) return false;
        if (end && date > end) return false;
        return true;
    };

    // Filter daily activity
    const filteredDailyActivity = (stats.dailyActivity || []).filter(d => filterByDate(d.date));

    // Filter daily model tokens
    const filteredDailyModelTokens = (stats.dailyModelTokens || []).filter(d => filterByDate(d.date));

    // Filter projects by their session dates
    const filteredProjectStats = (stats.projectStats || []).filter(p => {
        if (!p.firstSession && !p.lastSession) return true;
        if (p.lastSession && start && new Date(p.lastSession) < start) return false;
        if (p.firstSession && end && new Date(p.firstSession) > end) return false;
        return true;
    });

    // Recalculate totals from filtered data
    const totalMessages = filteredDailyActivity.reduce((sum, d) => sum + (d.messageCount || 0), 0);
    const totalSessions = filteredDailyActivity.reduce((sum, d) => sum + (d.sessionCount || 0), 0);
    const totalToolCalls = filteredDailyActivity.reduce((sum, d) => sum + (d.toolCallCount || 0), 0);

    // Filter and recalculate cost estimate
    let filteredCostEstimate = stats.costEstimate;
    if (stats.costEstimate && stats.costEstimate.costByDay) {
        const filteredCostByDay = stats.costEstimate.costByDay.filter(d => filterByDate(d.date));
        const filteredTotalCost = filteredCostByDay.reduce((sum, d) => sum + (d.cost || 0), 0);

        // Recalculate cost by model from filtered daily data
        const filteredCostByModel = {};
        filteredCostByDay.forEach(d => {
            if (d.costByModel) {
                Object.entries(d.costByModel).forEach(([model, cost]) => {
                    filteredCostByModel[model] = (filteredCostByModel[model] || 0) + cost;
                });
            }
        });

        // Recalculate cache savings proportionally
        const totalDays = (stats.costEstimate.costByDay || []).length;
        const filteredDays = filteredCostByDay.length;
        const savingsRatio = totalDays > 0 ? filteredDays / totalDays : 0;
        const filteredCacheSavings = stats.costEstimate.cacheSavingsUsd * savingsRatio;

        filteredCostEstimate = {
            ...stats.costEstimate,
            totalCostUsd: filteredTotalCost,
            costByModel: Object.keys(filteredCostByModel).length > 0 ? filteredCostByModel : stats.costEstimate.costByModel,
            costByDay: filteredCostByDay,
            cacheSavingsUsd: filteredCacheSavings,
        };
    }

    // Filter and recalculate cache metrics from daily model tokens
    let filteredCacheMetrics = stats.cacheMetrics;
    if (stats.cacheMetrics && filteredDailyModelTokens.length > 0) {
        // Estimate cache metrics proportionally based on filtered days
        const totalDays = (stats.dailyModelTokens || []).length;
        const filteredDays = filteredDailyModelTokens.length;
        const ratio = totalDays > 0 ? filteredDays / totalDays : 0;

        filteredCacheMetrics = {
            ...stats.cacheMetrics,
            totalCacheReadTokens: Math.round(stats.cacheMetrics.totalCacheReadTokens * ratio),
            totalCacheWriteTokens: Math.round(stats.cacheMetrics.totalCacheWriteTokens * ratio),
            tokensSaved: Math.round(stats.cacheMetrics.tokensSaved * ratio),
            // Cache hit ratio stays the same (it's a ratio, not absolute)
        };
    }

    // Filter turn durations
    const filteredTurnDurations = (stats.turnDurations || []).filter(d => filterByDate(d.date));

    // Filter API errors
    const filteredApiErrors = (stats.apiErrors || []).filter(d => filterByDate(d.date));

    // Filter plan stats
    let filteredPlanStats = stats.planStats;
    if (stats.planStats && stats.planStats.byDate) {
        const filteredByDate = stats.planStats.byDate.filter(d => filterByDate(d.date));
        const filteredTotalPlans = filteredByDate.reduce((sum, d) => sum + (d.count || 0), 0);
        filteredPlanStats = {
            ...stats.planStats,
            totalPlans: filteredTotalPlans,
            byDate: filteredByDate,
        };
    }

    return {
        ...stats,
        dailyActivity: filteredDailyActivity,
        dailyModelTokens: filteredDailyModelTokens,
        projectStats: filteredProjectStats,
        totalMessages: totalMessages || stats.totalMessages,
        totalSessions: totalSessions || stats.totalSessions,
        totalToolCalls: totalToolCalls || stats.totalToolCalls,
        totalProjects: filteredProjectStats.length,
        costEstimate: filteredCostEstimate,
        cacheMetrics: filteredCacheMetrics,
        turnDurations: filteredTurnDurations,
        apiErrors: filteredApiErrors,
        planStats: filteredPlanStats,
    };
}

async function loadStats() {
    if (window.CLAUDE_STATS) {
        return window.CLAUDE_STATS;
    }

    try {
        const response = await fetch('stats.json');
        if (!response.ok) throw new Error('Failed to load stats');
        return await response.json();
    } catch (error) {
        console.error('Error loading stats:', error);
        document.body.innerHTML = `
            <div style="text-align: center; padding: 4rem; color: #a0a0a0;">
                <h1 style="color: #f59e0b;">Error Loading Stats</h1>
                <p>Could not load stats.json. Make sure it exists in the same directory as this file.</p>
                <p style="margin-top: 1rem; font-size: 0.875rem;">${error.message}</p>
            </div>
        `;
        return null;
    }
}

function updateStatCards(stats) {
    document.getElementById('totalSessions').textContent = formatNumber(stats.totalSessions);
    document.getElementById('totalMessages').textContent = formatNumber(stats.totalMessages);
    document.getElementById('totalToolCalls').textContent = formatNumber(stats.totalToolCalls);
    document.getElementById('totalProjects').textContent = stats.totalProjects;

    // Cost estimate
    if (stats.costEstimate) {
        document.getElementById('totalCost').textContent = formatCurrency(stats.costEstimate.totalCostUsd);
        document.getElementById('cacheSavings').textContent = formatCurrency(stats.costEstimate.cacheSavingsUsd);
    }

    // Date range display
    if (stats.dailyActivity && stats.dailyActivity.length > 0) {
        const firstDate = stats.dailyActivity[0].date;
        const lastDate = stats.dailyActivity[stats.dailyActivity.length - 1].date;
        document.getElementById('dateRange').textContent = `${formatDate(firstDate)} - ${formatDate(lastDate)}`;
    }

    if (stats.generatedAt) {
        document.getElementById('generatedAt').textContent = `Generated ${formatDate(stats.generatedAt)}`;
    }
}

function createActivityChart(stats) {
    const container = document.getElementById('activityChart').parentElement;
    const canvas = document.getElementById('activityChart');
    const ctx = canvas.getContext('2d');
    const data = stats.dailyActivity || [];

    destroyChart('activityChart');

    if (data.length === 0) {
        showEmptyState(container, 'Daily Activity', 'No activity data found');
        return;
    }

    // Restore canvas if it was replaced by empty state
    if (!document.getElementById('activityChart')) {
        container.innerHTML = '<h2>Daily Activity</h2><canvas id="activityChart"></canvas>';
    }

    chartInstances['activityChart'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.date),
            datasets: [
                {
                    label: 'Messages',
                    data: data.map(d => d.messageCount),
                    borderColor: COLORS.accent,
                    backgroundColor: COLORS.accent + '20',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y',
                },
                {
                    label: 'Sessions',
                    data: data.map(d => d.sessionCount),
                    borderColor: COLORS.purple,
                    backgroundColor: 'transparent',
                    tension: 0.3,
                    yAxisID: 'y1',
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatNumber(context.raw)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d',
                        },
                    },
                    grid: {
                        display: false,
                    },
                },
                y: {
                    type: 'linear',
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Messages',
                        color: COLORS.accent,
                    },
                    grid: {
                        color: '#2d3748',
                    },
                    ticks: {
                        callback: val => formatNumber(val),
                    },
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Sessions',
                        color: COLORS.purple,
                    },
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}

function createModelChart(stats) {
    const container = document.getElementById('modelChart').parentElement;
    const ctx = document.getElementById('modelChart').getContext('2d');
    const modelUsage = stats.modelUsage || [];

    destroyChart('modelChart');

    if (modelUsage.length === 0) {
        showEmptyState(container, 'Model Usage', 'No model usage data found');
        return;
    }

    const labels = modelUsage.map(m => getModelDisplayName(m.model));
    const outputTokens = modelUsage.map(m => m.outputTokens);

    chartInstances['modelChart'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: outputTokens,
                backgroundColor: CHART_COLORS.slice(0, labels.length),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${formatNumber(context.raw)} tokens (${pct}%)`;
                        }
                    }
                }
            },
        },
    });
}

function createHoursChart(stats) {
    const container = document.getElementById('hoursChart').parentElement;
    const ctx = document.getElementById('hoursChart').getContext('2d');
    const hourCounts = stats.hourCounts || {};

    destroyChart('hoursChart');

    const hours = Array.from({ length: 24 }, (_, i) => i);
    const counts = hours.map(h => hourCounts[h.toString()] || 0);
    const totalSessions = counts.reduce((a, b) => a + b, 0);

    if (totalSessions === 0) {
        showEmptyState(container, 'Peak Hours', 'No session timing data found');
        return;
    }

    chartInstances['hoursChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours.map(h => `${h}:00`),
            datasets: [{
                label: 'Sessions Started',
                data: counts,
                backgroundColor: COLORS.cyan,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                    },
                    ticks: {
                        maxRotation: 0,
                        callback: function(val, index) {
                            return index % 4 === 0 ? this.getLabelForValue(val) : '';
                        },
                    },
                },
                y: {
                    grid: {
                        color: '#2d3748',
                    },
                },
            },
        },
    });
}

function createTokensChart(stats) {
    const container = document.getElementById('tokensChart').parentElement;
    const ctx = document.getElementById('tokensChart').getContext('2d');
    const data = stats.dailyModelTokens || [];

    destroyChart('tokensChart');

    if (data.length === 0) {
        showEmptyState(container, 'Token Usage Over Time', 'No token usage data found');
        return;
    }

    const allModels = new Set();
    data.forEach(d => {
        Object.keys(d.tokensByModel || {}).forEach(m => allModels.add(m));
    });

    if (allModels.size === 0) {
        showEmptyState(container, 'Token Usage Over Time', 'No token usage data found');
        return;
    }

    const modelList = Array.from(allModels);
    const datasets = modelList.map((model, i) => ({
        label: getModelDisplayName(model),
        data: data.map(d => (d.tokensByModel || {})[model] || 0),
        backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
        borderColor: CHART_COLORS[i % CHART_COLORS.length],
        fill: true,
        tension: 0.3,
    }));

    chartInstances['tokensChart'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.date),
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatNumber(context.raw)} tokens`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d',
                        },
                    },
                    grid: {
                        display: false,
                    },
                },
                y: {
                    stacked: true,
                    grid: {
                        color: '#2d3748',
                    },
                    ticks: {
                        callback: val => formatNumber(val),
                    },
                },
            },
        },
    });
}

function createProjectsChart(stats) {
    const container = document.getElementById('projectsChart').parentElement;
    const ctx = document.getElementById('projectsChart').getContext('2d');
    const projects = (stats.projectStats || []).slice(0, 10);

    destroyChart('projectsChart');

    if (projects.length === 0) {
        showEmptyState(container, 'Top Projects', 'No project data found');
        return;
    }

    chartInstances['projectsChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: projects.map(p => p.name),
            datasets: [{
                label: 'Messages',
                data: projects.map(p => p.messageCount),
                backgroundColor: COLORS.green,
                borderRadius: 4,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    grid: {
                        color: '#2d3748',
                    },
                    ticks: {
                        callback: val => formatNumber(val),
                    },
                },
                y: {
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}

function createSubagentChart(stats) {
    const container = document.getElementById('subagentChart').parentElement;
    const ctx = document.getElementById('subagentChart').getContext('2d');
    const toolUsage = stats.toolUsage || [];

    destroyChart('subagentChart');

    const subagents = toolUsage
        .filter(t => t.category === 'subagent')
        .map(t => ({
            name: t.name.replace('subagent:', ''),
            count: t.count,
        }))
        .slice(0, 8);

    if (subagents.length === 0) {
        showEmptyState(container, 'Subagent Usage', 'No subagent usage found');
        return;
    }

    chartInstances['subagentChart'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: subagents.map(s => s.name),
            datasets: [{
                data: subagents.map(s => s.count),
                backgroundColor: CHART_COLORS.slice(0, subagents.length),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 8,
                    },
                },
            },
        },
    });
}

function createToolsChart(stats) {
    const container = document.getElementById('toolsChart').parentElement;
    const ctx = document.getElementById('toolsChart').getContext('2d');
    const toolUsage = stats.toolUsage || [];

    destroyChart('toolsChart');

    const builtinTools = toolUsage
        .filter(t => t.category === 'builtin')
        .slice(0, 15);

    if (builtinTools.length === 0) {
        showEmptyState(container, 'Top Tools', 'No tool usage data found');
        return;
    }

    chartInstances['toolsChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: builtinTools.map(t => t.name),
            datasets: [{
                label: 'Calls',
                data: builtinTools.map(t => t.count),
                backgroundColor: COLORS.purple,
                borderRadius: 4,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    grid: {
                        color: '#2d3748',
                    },
                    ticks: {
                        callback: val => formatNumber(val),
                    },
                },
                y: {
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}

function createMcpChart(stats) {
    const container = document.getElementById('mcpChart').parentElement;
    const ctx = document.getElementById('mcpChart').getContext('2d');
    const toolUsage = stats.toolUsage || [];

    destroyChart('mcpChart');

    const mcpTools = toolUsage
        .filter(t => t.category === 'mcp')
        .slice(0, 15);

    if (mcpTools.length === 0) {
        showEmptyState(container, 'MCP Tools', 'No MCP tool usage found');
        return;
    }

    chartInstances['mcpChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: mcpTools.map(t => getMcpToolName(t.name)),
            datasets: [{
                label: 'Calls',
                data: mcpTools.map(t => t.count),
                backgroundColor: COLORS.orange,
                borderRadius: 4,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const idx = context[0].dataIndex;
                            return mcpTools[idx].name;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#2d3748',
                    },
                    ticks: {
                        callback: val => formatNumber(val),
                    },
                },
                y: {
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}

function createMcpServersChart(stats) {
    const container = document.getElementById('mcpServersChart').parentElement;
    const ctx = document.getElementById('mcpServersChart').getContext('2d');
    const toolUsage = stats.toolUsage || [];

    destroyChart('mcpServersChart');

    const mcpTools = toolUsage.filter(t => t.category === 'mcp');

    if (mcpTools.length === 0) {
        showEmptyState(container, 'MCP Servers', 'No MCP usage found');
        return;
    }

    const serverCounts = {};
    mcpTools.forEach(t => {
        const server = getMcpServerName(t.name);
        serverCounts[server] = (serverCounts[server] || 0) + t.count;
    });

    const servers = Object.entries(serverCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8);

    chartInstances['mcpServersChart'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: servers.map(s => s[0]),
            datasets: [{
                data: servers.map(s => s[1]),
                backgroundColor: CHART_COLORS.slice(0, servers.length),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 8,
                    },
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${formatNumber(context.raw)} calls (${pct}%)`;
                        }
                    }
                }
            },
        },
    });
}

function createCommandsChart(stats) {
    const container = document.getElementById('commandsChart').parentElement;
    const ctx = document.getElementById('commandsChart').getContext('2d');
    const commands = (stats.slashCommandUsage || []).slice(0, 8);

    destroyChart('commandsChart');

    if (commands.length === 0) {
        showEmptyState(container, 'Slash Commands', 'No slash command usage found');
        return;
    }

    chartInstances['commandsChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: commands.map(c => c.command),
            datasets: [{
                label: 'Uses',
                data: commands.map(c => c.count),
                backgroundColor: COLORS.pink,
                borderRadius: 4,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    grid: {
                        color: '#2d3748',
                    },
                },
                y: {
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}

function updatePluginsList(stats) {
    const container = document.getElementById('pluginsList');
    const enabled = stats.enabledPlugins || [];
    const installed = stats.installedPlugins || [];

    if (installed.length === 0 && enabled.length === 0) {
        return;
    }

    const allPlugins = new Set([...installed, ...enabled]);
    container.innerHTML = Array.from(allPlugins)
        .map(plugin => {
            const isEnabled = enabled.includes(plugin);
            return `<span class="plugin-tag ${isEnabled ? 'enabled' : ''}">${plugin}</span>`;
        })
        .join('');
}

// New v2 chart functions

function createCostByModelChart(stats) {
    const container = document.getElementById('costByModelChart').parentElement;
    const ctx = document.getElementById('costByModelChart').getContext('2d');
    const costEstimate = stats.costEstimate;

    destroyChart('costByModelChart');

    if (!costEstimate || !costEstimate.costByModel || Object.keys(costEstimate.costByModel).length === 0) {
        showEmptyState(container, 'Cost by Model', 'No cost data available');
        return;
    }

    const models = Object.entries(costEstimate.costByModel)
        .filter(([_, cost]) => cost > 0)
        .sort((a, b) => b[1] - a[1]);

    if (models.length === 0) {
        showEmptyState(container, 'Cost by Model', 'No cost data available');
        return;
    }

    chartInstances['costByModelChart'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: models.map(([model]) => getModelDisplayName(model)),
            datasets: [{
                data: models.map(([_, cost]) => cost),
                backgroundColor: CHART_COLORS.slice(0, models.length),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${formatCurrency(context.raw)} (${pct}%)`;
                        }
                    }
                }
            },
        },
    });
}

function createCacheChart(stats) {
    const container = document.getElementById('cacheChart').parentElement;
    const ctx = document.getElementById('cacheChart').getContext('2d');
    const cacheMetrics = stats.cacheMetrics;

    destroyChart('cacheChart');

    if (!cacheMetrics || cacheMetrics.totalCacheReadTokens === 0) {
        showEmptyState(container, 'Cache Efficiency', 'No cache data available');
        return;
    }

    const hitRatio = cacheMetrics.cacheHitRatio;
    const missRatio = 1 - hitRatio;

    chartInstances['cacheChart'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Cache Hits', 'Cache Misses'],
            datasets: [{
                data: [hitRatio, missRatio],
                backgroundColor: [COLORS.green, COLORS.red],
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${formatPercent(context.raw)}`;
                        }
                    }
                }
            },
        },
    });
}

function createDurationChart(stats) {
    const container = document.getElementById('durationChart').parentElement;
    const ctx = document.getElementById('durationChart').getContext('2d');
    const durations = stats.turnDurations || [];

    destroyChart('durationChart');

    if (durations.length === 0) {
        showEmptyState(container, 'Response Time (Turn Duration)', 'No turn duration data available');
        return;
    }

    chartInstances['durationChart'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: durations.map(d => d.date),
            datasets: [
                {
                    label: 'Average',
                    data: durations.map(d => d.avgDurationMs / 1000),
                    borderColor: COLORS.accent,
                    backgroundColor: COLORS.accent + '20',
                    fill: true,
                    tension: 0.3,
                },
                {
                    label: 'P50',
                    data: durations.map(d => d.p50Ms / 1000),
                    borderColor: COLORS.green,
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.3,
                },
                {
                    label: 'P95',
                    data: durations.map(d => d.p95Ms / 1000),
                    borderColor: COLORS.red,
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw.toFixed(1)}s`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d',
                        },
                    },
                    grid: {
                        display: false,
                    },
                },
                y: {
                    title: {
                        display: true,
                        text: 'Duration (seconds)',
                    },
                    grid: {
                        color: '#2d3748',
                    },
                },
            },
        },
    });
}

function createReliabilityChart(stats) {
    const container = document.getElementById('reliabilityChart').parentElement;
    const ctx = document.getElementById('reliabilityChart').getContext('2d');
    const apiErrors = stats.apiErrors || [];

    destroyChart('reliabilityChart');

    if (apiErrors.length === 0) {
        showEmptyState(container, 'API Reliability', 'No API errors recorded (good!)');
        return;
    }

    // Group by error type
    const errorsByType = {};
    apiErrors.forEach(e => {
        if (!errorsByType[e.errorType]) {
            errorsByType[e.errorType] = 0;
        }
        errorsByType[e.errorType] += e.count;
    });

    const types = Object.entries(errorsByType).sort((a, b) => b[1] - a[1]);

    chartInstances['reliabilityChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: types.map(([type]) => type),
            datasets: [{
                label: 'Error Count',
                data: types.map(([_, count]) => count),
                backgroundColor: COLORS.red,
                borderRadius: 4,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    grid: {
                        color: '#2d3748',
                    },
                },
                y: {
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}

function createTasksChart(stats) {
    const container = document.getElementById('tasksChart').parentElement;
    const ctx = document.getElementById('tasksChart').getContext('2d');
    const taskStats = stats.taskStats;

    destroyChart('tasksChart');

    if (!taskStats || taskStats.totalCreated === 0) {
        showEmptyState(container, 'Task Completion', 'No task data available');
        return;
    }

    const statusData = taskStats.byStatus || {};

    // Map status names to display names
    const statusLabels = {
        completed: 'Completed',
        in_progress: 'In Progress',
        pending: 'Pending',
        cancelled: 'Cancelled',
    };

    const statusColors = {
        completed: COLORS.green,
        in_progress: COLORS.accent,
        pending: COLORS.purple,
        cancelled: COLORS.red,
    };

    // Sort by a logical order, not count
    const statusOrder = ['completed', 'in_progress', 'pending', 'cancelled'];
    const statuses = statusOrder
        .filter(status => statusData[status] > 0)
        .map(status => [status, statusData[status]]);

    // Add any unknown statuses at the end
    Object.entries(statusData).forEach(([status, count]) => {
        if (!statusOrder.includes(status) && count > 0) {
            statuses.push([status, count]);
        }
    });

    chartInstances['tasksChart'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: statuses.map(([status]) => statusLabels[status] || status),
            datasets: [{
                data: statuses.map(([_, count]) => count),
                backgroundColor: statuses.map(([status]) => statusColors[status] || COLORS.cyan),
                borderWidth: 0,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                },
                title: {
                    display: true,
                    text: `${formatPercent(taskStats.completionRate)} completion rate`,
                    color: '#a0a0a0',
                    font: {
                        size: 12,
                    },
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} (${pct}%)`;
                        }
                    }
                }
            },
        },
    });
}

function createPlansChart(stats) {
    const container = document.getElementById('plansChart').parentElement;
    const ctx = document.getElementById('plansChart').getContext('2d');
    const planStats = stats.planStats;

    destroyChart('plansChart');

    if (!planStats || planStats.totalPlans === 0) {
        showEmptyState(container, 'Plan Activity', 'No plans created yet');
        return;
    }

    const byDate = planStats.byDate || [];
    if (byDate.length === 0) {
        showEmptyState(container, 'Plan Activity', 'No plan date data');
        return;
    }

    chartInstances['plansChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: byDate.map(d => d.date),
            datasets: [{
                label: 'Plans Created',
                data: byDate.map(d => d.count),
                backgroundColor: COLORS.purple,
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                },
                title: {
                    display: true,
                    text: `Total: ${planStats.totalPlans} plans (avg ${planStats.avgPlanLines} lines)`,
                    color: '#a0a0a0',
                    font: {
                        size: 12,
                    },
                },
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d',
                        },
                    },
                    grid: {
                        display: false,
                    },
                },
                y: {
                    grid: {
                        color: '#2d3748',
                    },
                    beginAtZero: true,
                },
            },
        },
    });
}

function createToolSuccessChart(stats) {
    const container = document.getElementById('toolSuccessChart').parentElement;
    const ctx = document.getElementById('toolSuccessChart').getContext('2d');
    const toolSuccessRates = stats.toolSuccessRates || [];

    destroyChart('toolSuccessChart');

    // Only show tools with at least some errors (interesting data)
    const toolsWithErrors = toolSuccessRates.filter(t => t.errorCount > 0).slice(0, 10);

    if (toolsWithErrors.length === 0) {
        showEmptyState(container, 'Tool Success Rate', 'All tools have 100% success rate!');
        return;
    }

    chartInstances['toolSuccessChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: toolsWithErrors.map(t => t.toolName),
            datasets: [
                {
                    label: 'Success',
                    data: toolsWithErrors.map(t => t.successCount),
                    backgroundColor: COLORS.green,
                    borderRadius: 4,
                },
                {
                    label: 'Errors',
                    data: toolsWithErrors.map(t => t.errorCount),
                    backgroundColor: COLORS.red,
                    borderRadius: 4,
                },
            ],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        afterBody: function(context) {
                            const idx = context[0].dataIndex;
                            const tool = toolsWithErrors[idx];
                            return `Success Rate: ${formatPercent(tool.successRate)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: {
                        color: '#2d3748',
                    },
                },
                y: {
                    stacked: true,
                    grid: {
                        display: false,
                    },
                },
            },
        },
    });
}

function updateFileEditStats(stats) {
    const container = document.getElementById('fileEditStats');
    const fileEditStats = stats.fileEditStats;

    if (!fileEditStats || fileEditStats.totalFilesEdited === 0) {
        return;
    }

    container.innerHTML = `
        <div class="stat-row">
            <span class="label">Files Edited</span>
            <span class="value">${formatNumber(fileEditStats.totalFilesEdited)}</span>
        </div>
        <div class="stat-row">
            <span class="label">Total Versions</span>
            <span class="value">${formatNumber(fileEditStats.totalVersions)}</span>
        </div>
        <div class="stat-row">
            <span class="label">Sessions with Edits</span>
            <span class="value">${Object.keys(fileEditStats.bySession).length}</span>
        </div>
    `;
}

function updateThinkingStats(stats) {
    const container = document.getElementById('thinkingStats');
    const thinkingUsage = stats.thinkingUsage;

    if (!thinkingUsage || thinkingUsage.totalThinkingBlocks === 0) {
        return;
    }

    container.innerHTML = `
        <div class="stat-row">
            <span class="label">Sessions with Thinking</span>
            <span class="value">${formatNumber(thinkingUsage.sessionsWithThinking)}</span>
        </div>
        <div class="stat-row">
            <span class="label">Total Thinking Blocks</span>
            <span class="value">${formatNumber(thinkingUsage.totalThinkingBlocks)}</span>
        </div>
        <div class="stat-row">
            <span class="label">Est. Thinking Tokens</span>
            <span class="value">${formatNumber(thinkingUsage.totalThinkingTokens)}</span>
        </div>
    `;
}

function updateSessionDepthStats(stats) {
    const container = document.getElementById('sessionDepthStats');
    const sessionDepth = stats.sessionDepth;

    if (!sessionDepth || sessionDepth.maxDepth === 0) {
        return;
    }

    container.innerHTML = `
        <div class="stat-row">
            <span class="label">Max Conversation Depth</span>
            <span class="value">${sessionDepth.maxDepth}</span>
        </div>
        <div class="stat-row">
            <span class="label">Average Depth</span>
            <span class="value">${sessionDepth.avgDepth.toFixed(1)}</span>
        </div>
        <div class="stat-row">
            <span class="label">Sessions with Branching</span>
            <span class="value">${formatNumber(sessionDepth.sessionsWithChildren)}</span>
        </div>
    `;
}

function renderDashboard(stats) {
    updateStatCards(stats);
    createActivityChart(stats);
    createModelChart(stats);
    createHoursChart(stats);
    createTokensChart(stats);
    createProjectsChart(stats);
    createSubagentChart(stats);
    createToolsChart(stats);
    createMcpChart(stats);
    createMcpServersChart(stats);
    createCommandsChart(stats);
    updatePluginsList(stats);

    // New v2 charts
    createCostByModelChart(stats);
    createCacheChart(stats);
    createDurationChart(stats);
    createReliabilityChart(stats);
    createTasksChart(stats);
    createPlansChart(stats);
    createToolSuccessChart(stats);
    updateFileEditStats(stats);
    updateThinkingStats(stats);
    updateSessionDepthStats(stats);
}

function setupDateFilter() {
    const startInput = document.getElementById('startDate');
    const endInput = document.getElementById('endDate');
    const resetBtn = document.getElementById('resetDates');

    if (!originalStats || !originalStats.dailyActivity || originalStats.dailyActivity.length === 0) {
        return;
    }

    // Set min/max based on data range
    const dates = originalStats.dailyActivity.map(d => d.date).sort();
    const minDate = dates[0];
    const maxDate = dates[dates.length - 1];

    startInput.min = minDate;
    startInput.max = maxDate;
    endInput.min = minDate;
    endInput.max = maxDate;

    // Set initial values to full range
    startInput.value = minDate;
    endInput.value = maxDate;

    const applyFilter = () => {
        const filteredStats = filterStatsByDateRange(
            originalStats,
            startInput.value,
            endInput.value
        );
        renderDashboard(filteredStats);
    };

    startInput.addEventListener('change', applyFilter);
    endInput.addEventListener('change', applyFilter);

    resetBtn.addEventListener('click', () => {
        startInput.value = minDate;
        endInput.value = maxDate;
        renderDashboard(originalStats);
    });
}

async function init() {
    const stats = await loadStats();
    if (!stats) return;

    originalStats = stats;
    renderDashboard(stats);
    setupDateFilter();
}

document.addEventListener('DOMContentLoaded', init);
