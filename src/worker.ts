interface AgentBoundary {
  agentId: string;
  privacyLevel: 'public' | 'restricted' | 'private';
  sharingRules: SharingRule[];
  knowledgeIsolation: boolean;
  consentedAgents: string[];
  lastUpdated: number;
}

interface SharingRule {
  field: string;
  allowedAgents: string[];
  requiresConsent: boolean;
}

interface ConsentRequest {
  requesterId: string;
  targetId: string;
  scope: string[];
  expiresAt?: number;
}

interface BoundaryConfig {
  defaultPrivacy: 'public' | 'restricted' | 'private';
  requireExplicitConsent: boolean;
  autoExpireConsent: number; // hours
}

const DEFAULT_CONFIG: BoundaryConfig = {
  defaultPrivacy: 'restricted',
  requireExplicitConsent: true,
  autoExpireConsent: 24
};

class PersonalSpaceManager {
  private storage: KVNamespace;

  constructor(storage: KVNamespace) {
    this.storage = storage;
  }

  async getAgentSpace(agentId: string): Promise<AgentBoundary | null> {
    const data = await this.storage.get(`space:${agentId}`);
    return data ? JSON.parse(data) : null;
  }

  async createOrUpdateBoundary(boundary: AgentBoundary): Promise<void> {
    boundary.lastUpdated = Date.now();
    await this.storage.put(
      `space:${boundary.agentId}`,
      JSON.stringify(boundary)
    );
  }

  async checkAccess(requesterId: string, targetId: string, field: string): Promise<boolean> {
    const targetSpace = await this.getAgentSpace(targetId);
    if (!targetSpace) return false;

    // Agent always has access to their own space
    if (requesterId === targetId) return true;

    // Check privacy level
    if (targetSpace.privacyLevel === 'private') return false;
    if (targetSpace.privacyLevel === 'public') return true;

    // Check specific sharing rules
    const rule = targetSpace.sharingRules.find(r => r.field === field);
    if (rule) {
      if (rule.allowedAgents.includes(requesterId)) {
        if (rule.requiresConsent) {
          return targetSpace.consentedAgents.includes(requesterId);
        }
        return true;
      }
    }

    // Check general consent
    return targetSpace.consentedAgents.includes(requesterId);
  }

  async grantConsent(requesterId: string, targetId: string, scope: string[]): Promise<void> {
    const targetSpace = await this.getAgentSpace(targetId);
    if (!targetSpace) {
      throw new Error('Target agent space not found');
    }

    if (!targetSpace.consentedAgents.includes(requesterId)) {
      targetSpace.consentedAgents.push(requesterId);
      await this.createOrUpdateBoundary(targetSpace);
    }
  }

  async revokeConsent(requesterId: string, targetId: string): Promise<void> {
    const targetSpace = await this.getAgentSpace(targetId);
    if (targetSpace) {
      targetSpace.consentedAgents = targetSpace.consentedAgents.filter(id => id !== requesterId);
      await this.createOrUpdateBoundary(targetSpace);
    }
  }
}

const htmlResponse = (content: string): Response => {
  return new Response(content, {
    headers: {
      'Content-Type': 'text/html;charset=UTF-8',
      'X-Frame-Options': 'DENY',
      'Content-Security-Policy': "default-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com;"
    }
  });
};

const jsonResponse = (data: any, status = 200): Response => {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'X-Frame-Options': 'DENY',
      'Content-Security-Policy': "default-src 'self'"
    }
  });
};

const errorResponse = (message: string, status = 400): Response => {
  return jsonResponse({ error: message }, status);
};
const sh = {"Content-Security-Policy":"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; frame-ancestors 'none'","X-Frame-Options":"DENY"};
export default { async fetch(r: Request) { const u = new URL(r.url); if (u.pathname==='/health') return new Response(JSON.stringify({status:'ok'}),{headers:{'Content-Type':'application/json',...sh}}); return new Response(html,{headers:{'Content-Type':'text/html;charset=UTF-8',...sh}}); }};