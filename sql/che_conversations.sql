-- CHE Conversations Table
-- Stores persistent chat history for CHE assistant across sessions

CREATE TABLE IF NOT EXISTS che_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Metadata
    title TEXT DEFAULT 'New Conversation',
    is_system BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- CHE Messages Table
-- Stores individual messages within conversations
CREATE TABLE IF NOT EXISTS che_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Optional metadata for special messages
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT fk_conversation FOREIGN KEY (conversation_id) REFERENCES che_conversations(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_che_conversations_user_id ON che_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_che_conversations_updated_at ON che_conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_che_messages_conversation_id ON che_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_che_messages_created_at ON che_messages(created_at);

-- RLS Policies
ALTER TABLE che_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE che_messages ENABLE ROW LEVEL SECURITY;

-- Users can only see their own conversations
CREATE POLICY che_conversations_select_policy ON che_conversations
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY che_conversations_insert_policy ON che_conversations
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY che_conversations_update_policy ON che_conversations
    FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY che_conversations_delete_policy ON che_conversations
    FOR DELETE USING (auth.uid()::text = user_id);

-- Users can only see messages from their own conversations
CREATE POLICY che_messages_select_policy ON che_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM che_conversations 
            WHERE che_conversations.id = che_messages.conversation_id 
            AND che_conversations.user_id = auth.uid()::text
        )
    );

CREATE POLICY che_messages_insert_policy ON che_messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM che_conversations 
            WHERE che_conversations.id = che_messages.conversation_id 
            AND che_conversations.user_id = auth.uid()::text
        )
    );

CREATE POLICY che_messages_delete_policy ON che_messages
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM che_conversations 
            WHERE che_conversations.id = che_messages.conversation_id 
            AND che_conversations.user_id = auth.uid()::text
        )
    );

-- Function to update conversation timestamp
CREATE OR REPLACE FUNCTION update_che_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE che_conversations 
    SET updated_at = NOW() 
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update conversation timestamp when new message is added
CREATE TRIGGER update_che_conversation_on_message
    AFTER INSERT ON che_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_che_conversation_timestamp();

-- Comments
COMMENT ON TABLE che_conversations IS 'Stores CHE assistant conversation threads';
COMMENT ON TABLE che_messages IS 'Stores individual messages within CHE conversations';
COMMENT ON COLUMN che_conversations.user_id IS 'References auth.users.id (stored as TEXT for compatibility)';
COMMENT ON COLUMN che_conversations.is_system IS 'True for system conversations like Schedule Generation';
COMMENT ON COLUMN che_messages.role IS 'Message sender: user, assistant, or system';
COMMENT ON COLUMN che_messages.metadata IS 'Optional JSON data for actions, forms, etc.';
