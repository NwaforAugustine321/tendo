-- User profiles (id = Supabase Auth user UUID)
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email TEXT NOT NULL,
    name TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Business profiles
CREATE TABLE IF NOT EXISTS business_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    name TEXT DEFAULT '',
    logo_url TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    location TEXT DEFAULT '',
    onboarding_completed BOOLEAN DEFAULT false,
    category TEXT DEFAULT 'hybrid',
    description TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    name TEXT NOT NULL,
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    type TEXT DEFAULT 'customer',
    balance NUMERIC(12,2) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    name TEXT NOT NULL,
    unit TEXT DEFAULT '',
    unit_price NUMERIC(12,2) DEFAULT 0,
    category TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Services
CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    name TEXT NOT NULL,
    price NUMERIC(12,2) DEFAULT 0,
    category TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Inventory
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    product_id UUID REFERENCES products(id),
    quantity NUMERIC(12,2) DEFAULT 0,
    reorder_level NUMERIC(12,2) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    last_updated TIMESTAMPTZ DEFAULT now()
);



-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    customer_id UUID REFERENCES customers(id),
    type TEXT NOT NULL DEFAULT '',
    payment_type TEXT DEFAULT '',
    total NUMERIC(12,2) NOT NULL DEFAULT 0,
    status TEXT DEFAULT '',
    narration TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    invoice_number TEXT DEFAULT '',
    total NUMERIC(12,2) NOT NULL DEFAULT 0,
    status TEXT DEFAULT 'pending',
    due_date DATE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);



-- Payments
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    invoice_id UUID REFERENCES invoices(id),
    customer_id UUID REFERENCES customers(id),
    amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    payment_method TEXT DEFAULT 'cash',
    reference TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);



-- Conversation sessions
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    record_id UUID,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Conversation messages
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Operation checkpoints
CREATE TABLE IF NOT EXISTS operation_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id),
    message_id UUID REFERENCES conversation_messages(id),
    operation_type TEXT NOT NULL,
    user_input TEXT NOT NULL,
    ai_understanding_summary TEXT,
    before_state JSONB NOT NULL,
    after_state JSONB NOT NULL,
    status TEXT DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'reverted')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    user_id UUID NOT NULL REFERENCES user_profiles(id),
    operation_type TEXT NOT NULL,
    affected_entity JSONB NOT NULL,
    status TEXT DEFAULT 'success',
    failure_reason TEXT,
    event_id TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Business insights (produced by intelligence sub-agents)
CREATE TABLE IF NOT EXISTS business_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    insight TEXT NOT NULL,
    source_agent TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);



CREATE INDEX IF NOT EXISTS idx_business_insights_business_id ON business_insights(business_id);
CREATE INDEX IF NOT EXISTS idx_business_insights_created_at ON business_insights(created_at DESC);

-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE services ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE operation_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_insights ENABLE ROW LEVEL SECURITY;

-- RLS policies (service role bypasses, but these protect direct access)
CREATE POLICY "users_own_profile" ON user_profiles FOR ALL USING (id = auth.uid());
CREATE POLICY "users_own_businesses" ON business_profiles FOR ALL USING (user_id = auth.uid());
CREATE POLICY "business_scope" ON customers FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON products FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON services FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON inventory FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON transactions FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON invoices FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON payments FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON conversation_sessions FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON conversation_messages FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON operation_checkpoints FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
CREATE POLICY "business_scope" ON audit_logs FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));

CREATE POLICY "business_scope" ON business_insights FOR ALL USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
