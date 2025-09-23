--
-- PostgreSQL database dump
--

\restrict 3p3GDa4a9zs7KuNBDTqaxELKCf5g4ZoQ7lO5Cxc8ATJFme6kOUu9DH6ZG9MlLBm

-- Dumped from database version 15.14
-- Dumped by pg_dump version 17.6 (Debian 17.6-0+deb13u1)

-- Started on 2025-09-23 20:23:06 +0330

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE ONLY public.tenants_superadmin_user_permissions DROP CONSTRAINT tenants_superadmin_u_superadmin_id_4657e0c5_fk_tenants_s;
ALTER TABLE ONLY public.tenants_superadmin_user_permissions DROP CONSTRAINT tenants_superadmin_u_permission_id_bac6c7f5_fk_auth_perm;
ALTER TABLE ONLY public.tenants_superadmin_session DROP CONSTRAINT tenants_superadmin_s_super_admin_id_2172b352_fk_tenants_s;
ALTER TABLE ONLY public.tenants_superadmin_groups DROP CONSTRAINT tenants_superadmin_groups_group_id_de91425d_fk_auth_group_id;
ALTER TABLE ONLY public.tenants_superadmin_groups DROP CONSTRAINT tenants_superadmin_g_superadmin_id_e2577514_fk_tenants_s;
ALTER TABLE ONLY public.tenants_subscription_plan DROP CONSTRAINT tenants_subscription_created_by_id_34ba6c8d_fk_tenants_s;
ALTER TABLE ONLY public.tenants_invoice DROP CONSTRAINT "tenants_invoice_tenant_id_53aea1c2_fk_public.tenant_id";
ALTER TABLE ONLY public.tenants_invoice DROP CONSTRAINT tenants_invoice_subscription_plan_id_a1e39206_fk_tenants_s;
ALTER TABLE ONLY public.tenants_invoice DROP CONSTRAINT tenants_invoice_created_by_id_3443cc12_fk_tenants_superadmin_id;
ALTER TABLE ONLY public.tenants_billing_cycle DROP CONSTRAINT "tenants_billing_cycle_tenant_id_12cd2f33_fk_public.tenant_id";
ALTER TABLE ONLY public.system_backup_integrity_check DROP CONSTRAINT system_backup_integr_backup_record_id_6d7e1dd4_fk_system_ba;
ALTER TABLE ONLY public."public.tenant" DROP CONSTRAINT "public.tenant_subscription_plan_fk_7207af8b_fk_tenants_s";
ALTER TABLE ONLY public."public.domain" DROP CONSTRAINT "public.domain_tenant_id_da447c7f_fk_public.tenant_id";
ALTER TABLE ONLY public.auth_permission DROP CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co;
ALTER TABLE ONLY public.auth_group_permissions DROP CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id;
ALTER TABLE ONLY public.auth_group_permissions DROP CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm;
ALTER TABLE ONLY public.admin_system_health_alert DROP CONSTRAINT admin_system_health__source_metric_id_20da84e8_fk_admin_sys;
ALTER TABLE ONLY public.admin_restore_job DROP CONSTRAINT admin_restore_job_source_backup_id_19894d4b_fk_admin_bac;
DROP INDEX public.tenants_superadmin_username_8b8428ab_like;
DROP INDEX public.tenants_superadmin_user_permissions_superadmin_id_4657e0c5;
DROP INDEX public.tenants_superadmin_user_permissions_permission_id_bac6c7f5;
DROP INDEX public.tenants_superadmin_session_super_admin_id_2172b352;
DROP INDEX public.tenants_superadmin_groups_superadmin_id_e2577514;
DROP INDEX public.tenants_superadmin_groups_group_id_de91425d;
DROP INDEX public.tenants_sup_super_a_9440fa_idx;
DROP INDEX public.tenants_sup_session_d92be0_idx;
DROP INDEX public.tenants_sup_access__c786cc_idx;
DROP INDEX public.tenants_subscription_plan_plan_type_db3273fc_like;
DROP INDEX public.tenants_subscription_plan_created_by_id_34ba6c8d;
DROP INDEX public.tenants_invoice_tenant_id_53aea1c2;
DROP INDEX public.tenants_invoice_subscription_plan_id_a1e39206;
DROP INDEX public.tenants_invoice_invoice_number_5e928b09_like;
DROP INDEX public.tenants_invoice_created_by_id_3443cc12;
DROP INDEX public.tenants_inv_tenant__50abd5_idx;
DROP INDEX public.tenants_inv_status_8ea065_idx;
DROP INDEX public.tenants_inv_issue_d_412371_idx;
DROP INDEX public.tenants_inv_invoice_b03261_idx;
DROP INDEX public.tenants_inv_due_dat_964485_idx;
DROP INDEX public.tenants_acc_user_ty_85334c_idx;
DROP INDEX public.tenants_acc_timesta_281aad_idx;
DROP INDEX public.tenants_acc_tenant__351b58_idx;
DROP INDEX public.tenants_acc_success_6b5fea_idx;
DROP INDEX public.tenants_acc_action_3be01c_idx;
DROP INDEX public.system_backup_record_backup_id_37386484_like;
DROP INDEX public.system_backup_integrity_check_backup_record_id_6d7e1dd4;
DROP INDEX public.system_back_tenant__4eb251_idx;
DROP INDEX public.system_back_tenant__1aa49f_idx;
DROP INDEX public.system_back_schedul_a17780_idx;
DROP INDEX public.system_back_is_acti_c8cf8a_idx;
DROP INDEX public.system_back_expires_09de72_idx;
DROP INDEX public.system_back_created_8f1a80_idx;
DROP INDEX public.system_back_created_2959e5_idx;
DROP INDEX public.system_back_backup__fe79b2_idx;
DROP INDEX public.system_back_backup__2bea12_idx;
DROP INDEX public."public.tenant_subscription_plan_fk_id_7207af8b";
DROP INDEX public."public.tenant_schema_name_20c2de3c_like";
DROP INDEX public."public.domain_tenant_id_da447c7f";
DROP INDEX public."public.domain_is_primary_55af10c7";
DROP INDEX public."public.domain_domain_bb0b26a4_like";
DROP INDEX public.django_session_session_key_c0390e0f_like;
DROP INDEX public.django_session_expire_date_a5c62663;
DROP INDEX public.auth_permission_content_type_id_2f476e4b;
DROP INDEX public.auth_group_permissions_permission_id_84c5c92e;
DROP INDEX public.auth_group_permissions_group_id_b120cbf9;
DROP INDEX public.auth_group_name_a6ea08ec_like;
DROP INDEX public.admin_system_health_alert_source_metric_id_20da84e8;
DROP INDEX public.admin_syste_timesta_b8e39b_idx;
DROP INDEX public.admin_syste_status_de3753_idx;
DROP INDEX public.admin_syste_metric__27aa60_idx;
DROP INDEX public.admin_syste_categor_690516_idx;
DROP INDEX public.admin_syste_alert_i_5c9e56_idx;
DROP INDEX public.admin_restore_job_source_backup_id_19894d4b;
DROP INDEX public.admin_imper_tenant__e3a00e_idx;
DROP INDEX public.admin_imper_target__ed8738_idx;
DROP INDEX public.admin_imper_status_307a89_idx;
DROP INDEX public.admin_imper_session_194767_idx;
DROP INDEX public.admin_imper_admin_u_6ae6b4_idx;
DROP INDEX public.admin_backu_status_ed96bd_idx;
DROP INDEX public.admin_backu_job_id_f88ddd_idx;
DROP INDEX public.admin_backu_frequen_372e7d_idx;
DROP INDEX public.admin_backu_backup__9fc395_idx;
ALTER TABLE ONLY public.tenants_superadmin DROP CONSTRAINT tenants_superadmin_username_key;
ALTER TABLE ONLY public.tenants_superadmin_user_permissions DROP CONSTRAINT tenants_superadmin_user_permissions_pkey;
ALTER TABLE ONLY public.tenants_superadmin_user_permissions DROP CONSTRAINT tenants_superadmin_user__superadmin_id_permission_283d3791_uniq;
ALTER TABLE ONLY public.tenants_superadmin_session DROP CONSTRAINT tenants_superadmin_session_pkey;
ALTER TABLE ONLY public.tenants_superadmin DROP CONSTRAINT tenants_superadmin_pkey;
ALTER TABLE ONLY public.tenants_superadmin_groups DROP CONSTRAINT tenants_superadmin_groups_superadmin_id_group_id_006b168b_uniq;
ALTER TABLE ONLY public.tenants_superadmin_groups DROP CONSTRAINT tenants_superadmin_groups_pkey;
ALTER TABLE ONLY public.tenants_subscription_plan DROP CONSTRAINT tenants_subscription_plan_plan_type_key;
ALTER TABLE ONLY public.tenants_subscription_plan DROP CONSTRAINT tenants_subscription_plan_pkey;
ALTER TABLE ONLY public.tenants_publicsuspiciousactivity DROP CONSTRAINT tenants_publicsuspiciousactivity_pkey;
ALTER TABLE ONLY public.tenants_publicsecurityevent DROP CONSTRAINT tenants_publicsecurityevent_pkey;
ALTER TABLE ONLY public.tenants_publicratelimitattempt DROP CONSTRAINT tenants_publicratelimitattempt_pkey;
ALTER TABLE ONLY public.tenants_publicratelimitattempt DROP CONSTRAINT tenants_publicratelimita_identifier_limit_type_en_fb09cf82_uniq;
ALTER TABLE ONLY public.tenants_publicauditlog DROP CONSTRAINT tenants_publicauditlog_pkey;
ALTER TABLE ONLY public.tenants_invoice DROP CONSTRAINT tenants_invoice_uuid_key;
ALTER TABLE ONLY public.tenants_invoice DROP CONSTRAINT tenants_invoice_pkey;
ALTER TABLE ONLY public.tenants_invoice DROP CONSTRAINT tenants_invoice_invoice_number_key;
ALTER TABLE ONLY public.tenants_billing_cycle DROP CONSTRAINT tenants_billing_cycle_tenant_id_key;
ALTER TABLE ONLY public.tenants_billing_cycle DROP CONSTRAINT tenants_billing_cycle_pkey;
ALTER TABLE ONLY public.tenants_access_log DROP CONSTRAINT tenants_access_log_pkey;
ALTER TABLE ONLY public.system_backup_schedule DROP CONSTRAINT system_backup_schedule_pkey;
ALTER TABLE ONLY public.system_backup_record DROP CONSTRAINT system_backup_record_pkey;
ALTER TABLE ONLY public.system_backup_record DROP CONSTRAINT system_backup_record_backup_id_key;
ALTER TABLE ONLY public.system_backup_integrity_check DROP CONSTRAINT system_backup_integrity_check_pkey;
ALTER TABLE ONLY public."public.tenant" DROP CONSTRAINT "public.tenant_schema_name_key";
ALTER TABLE ONLY public."public.tenant" DROP CONSTRAINT "public.tenant_pkey";
ALTER TABLE ONLY public."public.domain" DROP CONSTRAINT "public.domain_pkey";
ALTER TABLE ONLY public."public.domain" DROP CONSTRAINT "public.domain_domain_key";
ALTER TABLE ONLY public.health_check_db_testmodel DROP CONSTRAINT health_check_db_testmodel_pkey;
ALTER TABLE ONLY public.django_session DROP CONSTRAINT django_session_pkey;
ALTER TABLE ONLY public.django_migrations DROP CONSTRAINT django_migrations_pkey;
ALTER TABLE ONLY public.django_content_type DROP CONSTRAINT django_content_type_pkey;
ALTER TABLE ONLY public.django_content_type DROP CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq;
ALTER TABLE ONLY public.auth_permission DROP CONSTRAINT auth_permission_pkey;
ALTER TABLE ONLY public.auth_permission DROP CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq;
ALTER TABLE ONLY public.auth_group DROP CONSTRAINT auth_group_pkey;
ALTER TABLE ONLY public.auth_group_permissions DROP CONSTRAINT auth_group_permissions_pkey;
ALTER TABLE ONLY public.auth_group_permissions DROP CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq;
ALTER TABLE ONLY public.auth_group DROP CONSTRAINT auth_group_name_key;
ALTER TABLE ONLY public.admin_tenant_snapshot DROP CONSTRAINT admin_tenant_snapshot_snapshot_id_key;
ALTER TABLE ONLY public.admin_tenant_snapshot DROP CONSTRAINT admin_tenant_snapshot_pkey;
ALTER TABLE ONLY public.admin_system_health_metric DROP CONSTRAINT admin_system_health_metric_pkey;
ALTER TABLE ONLY public.admin_system_health_alert DROP CONSTRAINT admin_system_health_alert_pkey;
ALTER TABLE ONLY public.admin_system_health_alert DROP CONSTRAINT admin_system_health_alert_alert_id_key;
ALTER TABLE ONLY public.admin_restore_job DROP CONSTRAINT admin_restore_job_pkey;
ALTER TABLE ONLY public.admin_restore_job DROP CONSTRAINT admin_restore_job_job_id_key;
ALTER TABLE ONLY public.admin_impersonation_session DROP CONSTRAINT admin_impersonation_session_session_id_key;
ALTER TABLE ONLY public.admin_impersonation_session DROP CONSTRAINT admin_impersonation_session_pkey;
ALTER TABLE ONLY public.admin_backup_schedule DROP CONSTRAINT admin_backup_schedule_pkey;
ALTER TABLE ONLY public.admin_backup_job DROP CONSTRAINT admin_backup_job_pkey;
ALTER TABLE ONLY public.admin_backup_job DROP CONSTRAINT admin_backup_job_job_id_key;
DROP TABLE public.tenants_superadmin_user_permissions;
DROP TABLE public.tenants_superadmin_session;
DROP TABLE public.tenants_superadmin_groups;
DROP TABLE public.tenants_superadmin;
DROP TABLE public.tenants_subscription_plan;
DROP TABLE public.tenants_publicsuspiciousactivity;
DROP TABLE public.tenants_publicsecurityevent;
DROP TABLE public.tenants_publicratelimitattempt;
DROP TABLE public.tenants_publicauditlog;
DROP TABLE public.tenants_invoice;
DROP TABLE public.tenants_billing_cycle;
DROP TABLE public.tenants_access_log;
DROP TABLE public.system_backup_schedule;
DROP TABLE public.system_backup_record;
DROP TABLE public.system_backup_integrity_check;
DROP TABLE public."public.tenant";
DROP TABLE public."public.domain";
DROP TABLE public.health_check_db_testmodel;
DROP TABLE public.django_session;
DROP TABLE public.django_migrations;
DROP TABLE public.django_content_type;
DROP TABLE public.auth_permission;
DROP TABLE public.auth_group_permissions;
DROP TABLE public.auth_group;
DROP TABLE public.admin_tenant_snapshot;
DROP TABLE public.admin_system_health_metric;
DROP TABLE public.admin_system_health_alert;
DROP TABLE public.admin_restore_job;
DROP TABLE public.admin_impersonation_session;
DROP TABLE public.admin_backup_schedule;
DROP TABLE public.admin_backup_job;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 227 (class 1259 OID 77356)
-- Name: admin_backup_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_backup_job (
    id bigint NOT NULL,
    job_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    backup_type character varying(20) NOT NULL,
    frequency character varying(20) NOT NULL,
    scheduled_time time without time zone,
    next_run timestamp with time zone,
    status character varying(20) NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    tenant_schema character varying(100) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size_bytes bigint,
    storage_backends jsonb NOT NULL,
    progress_percentage integer NOT NULL,
    log_messages jsonb NOT NULL,
    error_message text NOT NULL,
    metadata jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by_id integer,
    created_by_username character varying(150) NOT NULL,
    CONSTRAINT admin_backup_job_progress_percentage_check CHECK ((progress_percentage >= 0))
);


--
-- TOC entry 226 (class 1259 OID 77355)
-- Name: admin_backup_job_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.admin_backup_job ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.admin_backup_job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 229 (class 1259 OID 77367)
-- Name: admin_backup_schedule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_backup_schedule (
    id bigint NOT NULL,
    name character varying(200) NOT NULL,
    backup_type character varying(20) NOT NULL,
    frequency character varying(20) NOT NULL,
    scheduled_time time without time zone NOT NULL,
    is_active boolean NOT NULL,
    retention_days integer NOT NULL,
    max_backups integer NOT NULL,
    notify_on_success boolean NOT NULL,
    notify_on_failure boolean NOT NULL,
    notification_emails jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by_id integer,
    created_by_username character varying(150) NOT NULL,
    CONSTRAINT admin_backup_schedule_max_backups_check CHECK ((max_backups >= 0)),
    CONSTRAINT admin_backup_schedule_retention_days_check CHECK ((retention_days >= 0))
);


--
-- TOC entry 228 (class 1259 OID 77366)
-- Name: admin_backup_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.admin_backup_schedule ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.admin_backup_schedule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 225 (class 1259 OID 77341)
-- Name: admin_impersonation_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_impersonation_session (
    id bigint NOT NULL,
    session_id uuid NOT NULL,
    admin_user_id integer NOT NULL,
    admin_username character varying(150) NOT NULL,
    target_user_id integer NOT NULL,
    target_username character varying(150) NOT NULL,
    tenant_schema character varying(100) NOT NULL,
    tenant_domain character varying(253) NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone,
    status character varying(20) NOT NULL,
    ip_address inet NOT NULL,
    user_agent text NOT NULL,
    reason text NOT NULL,
    actions_performed jsonb NOT NULL,
    pages_visited jsonb NOT NULL,
    is_suspicious boolean NOT NULL,
    security_notes text NOT NULL
);


--
-- TOC entry 224 (class 1259 OID 77340)
-- Name: admin_impersonation_session_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.admin_impersonation_session ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.admin_impersonation_session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 231 (class 1259 OID 77377)
-- Name: admin_restore_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_restore_job (
    id bigint NOT NULL,
    job_id uuid NOT NULL,
    restore_type character varying(20) NOT NULL,
    target_tenant_schema character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    progress_percentage integer NOT NULL,
    log_messages jsonb NOT NULL,
    error_message text NOT NULL,
    confirmation_token character varying(100) NOT NULL,
    confirmed_by_typing character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by_id integer,
    created_by_username character varying(150) NOT NULL,
    source_backup_id bigint NOT NULL,
    CONSTRAINT admin_restore_job_progress_percentage_check CHECK ((progress_percentage >= 0))
);


--
-- TOC entry 230 (class 1259 OID 77376)
-- Name: admin_restore_job_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.admin_restore_job ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.admin_restore_job_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 235 (class 1259 OID 77420)
-- Name: admin_system_health_alert; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_system_health_alert (
    id bigint NOT NULL,
    alert_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    severity character varying(20) NOT NULL,
    category character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    acknowledged_at timestamp with time zone,
    resolved_at timestamp with time zone,
    threshold_value double precision,
    current_value double precision,
    notifications_sent jsonb NOT NULL,
    acknowledged_by_id integer,
    acknowledged_by_username character varying(150) NOT NULL,
    resolution_notes text NOT NULL,
    source_metric_id bigint
);


--
-- TOC entry 234 (class 1259 OID 77419)
-- Name: admin_system_health_alert_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.admin_system_health_alert ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.admin_system_health_alert_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 237 (class 1259 OID 77430)
-- Name: admin_system_health_metric; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_system_health_metric (
    id bigint NOT NULL,
    metric_type character varying(30) NOT NULL,
    value double precision NOT NULL,
    unit character varying(20) NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    hostname character varying(100) NOT NULL,
    metadata jsonb NOT NULL
);


--
-- TOC entry 236 (class 1259 OID 77429)
-- Name: admin_system_health_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.admin_system_health_metric ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.admin_system_health_metric_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 233 (class 1259 OID 77398)
-- Name: admin_tenant_snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_tenant_snapshot (
    id bigint NOT NULL,
    snapshot_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    snapshot_type character varying(20) NOT NULL,
    tenant_schema character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size_bytes bigint,
    created_by_id integer,
    created_by_username character varying(150) NOT NULL,
    metadata jsonb NOT NULL
);


--
-- TOC entry 232 (class 1259 OID 77397)
-- Name: admin_tenant_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.admin_tenant_snapshot ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.admin_tenant_snapshot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 221 (class 1259 OID 77301)
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


--
-- TOC entry 220 (class 1259 OID 77300)
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 223 (class 1259 OID 77309)
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


--
-- TOC entry 222 (class 1259 OID 77308)
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 219 (class 1259 OID 77295)
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


--
-- TOC entry 218 (class 1259 OID 77294)
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 217 (class 1259 OID 77287)
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


--
-- TOC entry 216 (class 1259 OID 77286)
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 215 (class 1259 OID 77279)
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


--
-- TOC entry 214 (class 1259 OID 77278)
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 240 (class 1259 OID 77455)
-- Name: django_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


--
-- TOC entry 239 (class 1259 OID 77450)
-- Name: health_check_db_testmodel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.health_check_db_testmodel (
    id integer NOT NULL,
    title character varying(128) NOT NULL
);


--
-- TOC entry 238 (class 1259 OID 77449)
-- Name: health_check_db_testmodel_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.health_check_db_testmodel ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.health_check_db_testmodel_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 250 (class 1259 OID 77517)
-- Name: public.domain; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."public.domain" (
    id bigint NOT NULL,
    domain character varying(253) NOT NULL,
    is_primary boolean NOT NULL,
    tenant_id bigint NOT NULL
);


--
-- TOC entry 249 (class 1259 OID 77516)
-- Name: public.domain_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public."public.domain" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public."public.domain_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 248 (class 1259 OID 77507)
-- Name: public.tenant; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."public.tenant" (
    id bigint NOT NULL,
    schema_name character varying(63) NOT NULL,
    name character varying(100) NOT NULL,
    created_on date NOT NULL,
    is_active boolean NOT NULL,
    owner_name character varying(100) NOT NULL,
    owner_email character varying(254) NOT NULL,
    phone_number character varying(15) NOT NULL,
    address text NOT NULL,
    subscription_plan character varying(20) NOT NULL,
    subscription_plan_fk_id bigint
);


--
-- TOC entry 247 (class 1259 OID 77506)
-- Name: public.tenant_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public."public.tenant" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public."public.tenant_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 246 (class 1259 OID 77483)
-- Name: system_backup_integrity_check; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_backup_integrity_check (
    id bigint NOT NULL,
    check_type character varying(50) NOT NULL,
    status character varying(20) NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    expected_hash character varying(128) NOT NULL,
    actual_hash character varying(128) NOT NULL,
    file_size_verified bigint,
    error_message text NOT NULL,
    metadata jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    backup_record_id bigint NOT NULL
);


--
-- TOC entry 245 (class 1259 OID 77482)
-- Name: system_backup_integrity_check_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.system_backup_integrity_check ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.system_backup_integrity_check_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 244 (class 1259 OID 77473)
-- Name: system_backup_record; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_backup_record (
    id bigint NOT NULL,
    backup_id character varying(100) NOT NULL,
    backup_type character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    frequency character varying(20) NOT NULL,
    tenant_schema character varying(100),
    tenant_domain character varying(100),
    file_path character varying(500) NOT NULL,
    file_size bigint,
    is_encrypted boolean NOT NULL,
    encryption_key_hash character varying(128) NOT NULL,
    file_hash character varying(128) NOT NULL,
    stored_in_primary boolean NOT NULL,
    stored_in_secondary boolean NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    expires_at timestamp with time zone,
    metadata jsonb NOT NULL,
    error_message text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(150) NOT NULL
);


--
-- TOC entry 243 (class 1259 OID 77472)
-- Name: system_backup_record_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.system_backup_record ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.system_backup_record_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 242 (class 1259 OID 77465)
-- Name: system_backup_schedule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_backup_schedule (
    id bigint NOT NULL,
    name character varying(200) NOT NULL,
    description text NOT NULL,
    schedule_type character varying(20) NOT NULL,
    frequency character varying(20) NOT NULL,
    hour integer NOT NULL,
    minute integer NOT NULL,
    day_of_week integer,
    day_of_month integer,
    tenant_schema character varying(100),
    retention_days integer NOT NULL,
    is_active boolean NOT NULL,
    last_run_at timestamp with time zone,
    next_run_at timestamp with time zone,
    last_backup_id character varying(100) NOT NULL,
    total_runs integer NOT NULL,
    successful_runs integer NOT NULL,
    failed_runs integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- TOC entry 241 (class 1259 OID 77464)
-- Name: system_backup_schedule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.system_backup_schedule ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.system_backup_schedule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 260 (class 1259 OID 77602)
-- Name: tenants_access_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_access_log (
    id bigint NOT NULL,
    user_type character varying(20) NOT NULL,
    user_id integer NOT NULL,
    username character varying(150) NOT NULL,
    tenant_schema character varying(100) NOT NULL,
    tenant_name character varying(200) NOT NULL,
    action character varying(50) NOT NULL,
    model_name character varying(100) NOT NULL,
    object_id character varying(100) NOT NULL,
    details jsonb NOT NULL,
    ip_address inet,
    user_agent text NOT NULL,
    request_path character varying(500) NOT NULL,
    request_method character varying(10) NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    duration_ms integer,
    success boolean NOT NULL,
    error_message text NOT NULL,
    CONSTRAINT tenants_access_log_duration_ms_check CHECK ((duration_ms >= 0)),
    CONSTRAINT tenants_access_log_user_id_check CHECK ((user_id >= 0))
);


--
-- TOC entry 259 (class 1259 OID 77601)
-- Name: tenants_access_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_access_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_access_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 264 (class 1259 OID 77637)
-- Name: tenants_billing_cycle; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_billing_cycle (
    id bigint NOT NULL,
    cycle_type character varying(20) NOT NULL,
    next_billing_date date NOT NULL,
    billing_day integer NOT NULL,
    auto_payment_enabled boolean NOT NULL,
    payment_method character varying(20) NOT NULL,
    grace_period_days integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    tenant_id bigint NOT NULL,
    CONSTRAINT tenants_billing_cycle_billing_day_check CHECK ((billing_day >= 0)),
    CONSTRAINT tenants_billing_cycle_grace_period_days_check CHECK ((grace_period_days >= 0))
);


--
-- TOC entry 263 (class 1259 OID 77636)
-- Name: tenants_billing_cycle_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_billing_cycle ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_billing_cycle_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 266 (class 1259 OID 77652)
-- Name: tenants_invoice; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_invoice (
    id bigint NOT NULL,
    invoice_number character varying(50) NOT NULL,
    uuid uuid NOT NULL,
    issue_date_shamsi date NOT NULL,
    due_date_shamsi date NOT NULL,
    billing_period_start date NOT NULL,
    billing_period_end date NOT NULL,
    subtotal_toman numeric(12,2) NOT NULL,
    tax_rate numeric(5,2) NOT NULL,
    tax_amount_toman numeric(12,2) NOT NULL,
    discount_amount_toman numeric(12,2) NOT NULL,
    total_amount_toman numeric(12,2) NOT NULL,
    status character varying(20) NOT NULL,
    payment_method character varying(20) NOT NULL,
    payment_date_shamsi date,
    payment_reference character varying(100) NOT NULL,
    bank_name character varying(100) NOT NULL,
    account_number character varying(50) NOT NULL,
    iban character varying(26) NOT NULL,
    line_items jsonb NOT NULL,
    notes text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    pdf_generated boolean NOT NULL,
    pdf_file_path character varying(500) NOT NULL,
    created_by_id bigint,
    subscription_plan_id bigint NOT NULL,
    tenant_id bigint NOT NULL
);


--
-- TOC entry 265 (class 1259 OID 77651)
-- Name: tenants_invoice_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_invoice ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_invoice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 268 (class 1259 OID 77703)
-- Name: tenants_publicauditlog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_publicauditlog (
    id bigint NOT NULL,
    action character varying(50) NOT NULL,
    model_name character varying(100) NOT NULL,
    object_id character varying(100) NOT NULL,
    object_repr character varying(200) NOT NULL,
    changes jsonb NOT NULL,
    ip_address inet,
    user_agent text NOT NULL,
    session_key character varying(40) NOT NULL,
    request_path character varying(500) NOT NULL,
    request_method character varying(10) NOT NULL,
    details jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- TOC entry 267 (class 1259 OID 77702)
-- Name: tenants_publicauditlog_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_publicauditlog ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_publicauditlog_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 274 (class 1259 OID 77727)
-- Name: tenants_publicratelimitattempt; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_publicratelimitattempt (
    id bigint NOT NULL,
    identifier character varying(200) NOT NULL,
    limit_type character varying(50) NOT NULL,
    endpoint character varying(200) NOT NULL,
    attempts integer NOT NULL,
    window_start timestamp with time zone NOT NULL,
    last_attempt timestamp with time zone NOT NULL,
    is_blocked boolean NOT NULL,
    blocked_until timestamp with time zone,
    user_agent text NOT NULL,
    details jsonb NOT NULL,
    CONSTRAINT tenants_publicratelimitattempt_attempts_check CHECK ((attempts >= 0))
);


--
-- TOC entry 273 (class 1259 OID 77726)
-- Name: tenants_publicratelimitattempt_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_publicratelimitattempt ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_publicratelimitattempt_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 270 (class 1259 OID 77711)
-- Name: tenants_publicsecurityevent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_publicsecurityevent (
    id bigint NOT NULL,
    event_type character varying(50) NOT NULL,
    severity character varying(20) NOT NULL,
    username_attempted character varying(150) NOT NULL,
    ip_address inet NOT NULL,
    user_agent text NOT NULL,
    session_key character varying(40) NOT NULL,
    request_path character varying(500) NOT NULL,
    request_method character varying(10) NOT NULL,
    details jsonb NOT NULL,
    is_resolved boolean NOT NULL,
    resolved_at timestamp with time zone,
    resolution_notes text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- TOC entry 269 (class 1259 OID 77710)
-- Name: tenants_publicsecurityevent_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_publicsecurityevent ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_publicsecurityevent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 272 (class 1259 OID 77719)
-- Name: tenants_publicsuspiciousactivity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_publicsuspiciousactivity (
    id bigint NOT NULL,
    activity_type character varying(50) NOT NULL,
    risk_level character varying(20) NOT NULL,
    ip_address inet NOT NULL,
    user_agent text NOT NULL,
    session_key character varying(40) NOT NULL,
    pattern_data jsonb NOT NULL,
    confidence_score double precision NOT NULL,
    is_investigated boolean NOT NULL,
    investigated_at timestamp with time zone,
    investigation_notes text NOT NULL,
    is_false_positive boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- TOC entry 271 (class 1259 OID 77718)
-- Name: tenants_publicsuspiciousactivity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_publicsuspiciousactivity ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_publicsuspiciousactivity_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 262 (class 1259 OID 77622)
-- Name: tenants_subscription_plan; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_subscription_plan (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    name_persian character varying(100) NOT NULL,
    plan_type character varying(20) NOT NULL,
    monthly_price_toman numeric(12,2) NOT NULL,
    yearly_price_toman numeric(12,2),
    max_users integer NOT NULL,
    max_inventory_items integer NOT NULL,
    max_customers integer NOT NULL,
    max_monthly_transactions integer NOT NULL,
    max_storage_gb integer NOT NULL,
    features jsonb NOT NULL,
    is_active boolean NOT NULL,
    is_popular boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by_id bigint,
    CONSTRAINT tenants_subscription_plan_max_customers_check CHECK ((max_customers >= 0)),
    CONSTRAINT tenants_subscription_plan_max_inventory_items_check CHECK ((max_inventory_items >= 0)),
    CONSTRAINT tenants_subscription_plan_max_monthly_transactions_check CHECK ((max_monthly_transactions >= 0)),
    CONSTRAINT tenants_subscription_plan_max_storage_gb_check CHECK ((max_storage_gb >= 0)),
    CONSTRAINT tenants_subscription_plan_max_users_check CHECK ((max_users >= 0))
);


--
-- TOC entry 261 (class 1259 OID 77621)
-- Name: tenants_subscription_plan_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_subscription_plan ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_subscription_plan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 252 (class 1259 OID 77534)
-- Name: tenants_superadmin; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_superadmin (
    id bigint NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL,
    phone_number character varying(15) NOT NULL,
    persian_first_name character varying(150) NOT NULL,
    persian_last_name character varying(150) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    can_access_all_data boolean NOT NULL,
    can_create_tenants boolean NOT NULL,
    can_suspend_tenants boolean NOT NULL,
    last_tenant_access timestamp with time zone,
    is_2fa_enabled boolean NOT NULL,
    theme_preference character varying(10) NOT NULL
);


--
-- TOC entry 254 (class 1259 OID 77544)
-- Name: tenants_superadmin_groups; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_superadmin_groups (
    id bigint NOT NULL,
    superadmin_id bigint NOT NULL,
    group_id integer NOT NULL
);


--
-- TOC entry 253 (class 1259 OID 77543)
-- Name: tenants_superadmin_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_superadmin_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_superadmin_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 251 (class 1259 OID 77533)
-- Name: tenants_superadmin_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_superadmin ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_superadmin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 258 (class 1259 OID 77556)
-- Name: tenants_superadmin_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_superadmin_session (
    id bigint NOT NULL,
    tenant_schema character varying(100) NOT NULL,
    session_key character varying(40) NOT NULL,
    ip_address inet,
    user_agent text NOT NULL,
    is_active boolean NOT NULL,
    super_admin_id bigint NOT NULL,
    access_time timestamp with time zone NOT NULL
);


--
-- TOC entry 257 (class 1259 OID 77555)
-- Name: tenants_superadmin_session_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_superadmin_session ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_superadmin_session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 256 (class 1259 OID 77550)
-- Name: tenants_superadmin_user_permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants_superadmin_user_permissions (
    id bigint NOT NULL,
    superadmin_id bigint NOT NULL,
    permission_id integer NOT NULL
);


--
-- TOC entry 255 (class 1259 OID 77549)
-- Name: tenants_superadmin_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.tenants_superadmin_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.tenants_superadmin_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 3761 (class 0 OID 77356)
-- Dependencies: 227
-- Data for Name: admin_backup_job; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.admin_backup_job (id, job_id, name, backup_type, frequency, scheduled_time, next_run, status, started_at, completed_at, tenant_schema, file_path, file_size_bytes, storage_backends, progress_percentage, log_messages, error_message, metadata, created_at, updated_at, created_by_id, created_by_username) FROM stdin;
\.


--
-- TOC entry 3763 (class 0 OID 77367)
-- Dependencies: 229
-- Data for Name: admin_backup_schedule; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.admin_backup_schedule (id, name, backup_type, frequency, scheduled_time, is_active, retention_days, max_backups, notify_on_success, notify_on_failure, notification_emails, created_at, updated_at, created_by_id, created_by_username) FROM stdin;
\.


--
-- TOC entry 3759 (class 0 OID 77341)
-- Dependencies: 225
-- Data for Name: admin_impersonation_session; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.admin_impersonation_session (id, session_id, admin_user_id, admin_username, target_user_id, target_username, tenant_schema, tenant_domain, start_time, end_time, status, ip_address, user_agent, reason, actions_performed, pages_visited, is_suspicious, security_notes) FROM stdin;
\.


--
-- TOC entry 3765 (class 0 OID 77377)
-- Dependencies: 231
-- Data for Name: admin_restore_job; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.admin_restore_job (id, job_id, restore_type, target_tenant_schema, status, started_at, completed_at, progress_percentage, log_messages, error_message, confirmation_token, confirmed_by_typing, created_at, updated_at, created_by_id, created_by_username, source_backup_id) FROM stdin;
\.


--
-- TOC entry 3769 (class 0 OID 77420)
-- Dependencies: 235
-- Data for Name: admin_system_health_alert; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.admin_system_health_alert (id, alert_id, title, description, severity, category, status, created_at, acknowledged_at, resolved_at, threshold_value, current_value, notifications_sent, acknowledged_by_id, acknowledged_by_username, resolution_notes, source_metric_id) FROM stdin;
\.


--
-- TOC entry 3771 (class 0 OID 77430)
-- Dependencies: 237
-- Data for Name: admin_system_health_metric; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.admin_system_health_metric (id, metric_type, value, unit, "timestamp", hostname, metadata) FROM stdin;
\.


--
-- TOC entry 3767 (class 0 OID 77398)
-- Dependencies: 233
-- Data for Name: admin_tenant_snapshot; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.admin_tenant_snapshot (id, snapshot_id, name, snapshot_type, tenant_schema, status, created_at, expires_at, file_path, file_size_bytes, created_by_id, created_by_username, metadata) FROM stdin;
\.


--
-- TOC entry 3755 (class 0 OID 77301)
-- Dependencies: 221
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- TOC entry 3757 (class 0 OID 77309)
-- Dependencies: 223
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- TOC entry 3753 (class 0 OID 77295)
-- Dependencies: 219
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add permission	1	add_permission
2	Can change permission	1	change_permission
3	Can delete permission	1	delete_permission
4	Can view permission	1	view_permission
5	Can add group	2	add_group
6	Can change group	2	change_group
7	Can delete group	2	delete_group
8	Can view group	2	view_group
9	Can add content type	3	add_contenttype
10	Can change content type	3	change_contenttype
11	Can delete content type	3	delete_contenttype
12	Can view content type	3	view_contenttype
13	Can add session	4	add_session
14	Can change session	4	change_session
15	Can delete session	4	delete_session
16	Can view session	4	view_session
17	Can add test model	5	add_testmodel
18	Can change test model	5	change_testmodel
19	Can delete test model	5	delete_testmodel
20	Can view test model	5	view_testmodel
21	Can add tenant	6	add_tenant
22	Can change tenant	6	change_tenant
23	Can delete tenant	6	delete_tenant
24	Can view tenant	6	view_tenant
25	Can add domain	7	add_domain
26	Can change domain	7	change_domain
27	Can delete domain	7	delete_domain
28	Can view domain	7	view_domain
29	Can add Super Admin	8	add_superadmin
30	Can change Super Admin	8	change_superadmin
31	Can delete Super Admin	8	delete_superadmin
32	Can view Super Admin	8	view_superadmin
33	Can add Super Admin Session	9	add_superadminsession
34	Can change Super Admin Session	9	change_superadminsession
35	Can delete Super Admin Session	9	delete_superadminsession
36	Can view Super Admin Session	9	view_superadminsession
37	Can add Tenant Access Log	10	add_tenantaccesslog
38	Can change Tenant Access Log	10	change_tenantaccesslog
39	Can delete Tenant Access Log	10	delete_tenantaccesslog
40	Can view Tenant Access Log	10	view_tenantaccesslog
41	Can add Subscription Plan	11	add_subscriptionplan
42	Can change Subscription Plan	11	change_subscriptionplan
43	Can delete Subscription Plan	11	delete_subscriptionplan
44	Can view Subscription Plan	11	view_subscriptionplan
45	Can add Billing Cycle	12	add_billingcycle
46	Can change Billing Cycle	12	change_billingcycle
47	Can delete Billing Cycle	12	delete_billingcycle
48	Can view Billing Cycle	12	view_billingcycle
49	Can add Tenant Invoice	13	add_tenantinvoice
50	Can change Tenant Invoice	13	change_tenantinvoice
51	Can delete Tenant Invoice	13	delete_tenantinvoice
52	Can view Tenant Invoice	13	view_tenantinvoice
53	Can add Public Audit Log	14	add_publicauditlog
54	Can change Public Audit Log	14	change_publicauditlog
55	Can delete Public Audit Log	14	delete_publicauditlog
56	Can view Public Audit Log	14	view_publicauditlog
57	Can add Public Security Event	15	add_publicsecurityevent
58	Can change Public Security Event	15	change_publicsecurityevent
59	Can delete Public Security Event	15	delete_publicsecurityevent
60	Can view Public Security Event	15	view_publicsecurityevent
61	Can add Public Suspicious Activity	16	add_publicsuspiciousactivity
62	Can change Public Suspicious Activity	16	change_publicsuspiciousactivity
63	Can delete Public Suspicious Activity	16	delete_publicsuspiciousactivity
64	Can view Public Suspicious Activity	16	view_publicsuspiciousactivity
65	Can add Public Rate Limit Attempt	17	add_publicratelimitattempt
66	Can change Public Rate Limit Attempt	17	change_publicratelimitattempt
67	Can delete Public Rate Limit Attempt	17	delete_publicratelimitattempt
68	Can view Public Rate Limit Attempt	17	view_publicratelimitattempt
69	Can add Impersonation Session	18	add_impersonationsession
70	Can change Impersonation Session	18	change_impersonationsession
71	Can delete Impersonation Session	18	delete_impersonationsession
72	Can view Impersonation Session	18	view_impersonationsession
73	Can add Backup Job	19	add_backupjob
74	Can change Backup Job	19	change_backupjob
75	Can delete Backup Job	19	delete_backupjob
76	Can view Backup Job	19	view_backupjob
77	Can add Backup Schedule	20	add_backupschedule
78	Can change Backup Schedule	20	change_backupschedule
79	Can delete Backup Schedule	20	delete_backupschedule
80	Can view Backup Schedule	20	view_backupschedule
81	Can add Restore Job	21	add_restorejob
82	Can change Restore Job	21	change_restorejob
83	Can delete Restore Job	21	delete_restorejob
84	Can view Restore Job	21	view_restorejob
85	Can add Tenant Snapshot	22	add_tenantsnapshot
86	Can change Tenant Snapshot	22	change_tenantsnapshot
87	Can delete Tenant Snapshot	22	delete_tenantsnapshot
88	Can view Tenant Snapshot	22	view_tenantsnapshot
89	Can add System Health Alert	23	add_systemhealthalert
90	Can change System Health Alert	23	change_systemhealthalert
91	Can delete System Health Alert	23	delete_systemhealthalert
92	Can view System Health Alert	23	view_systemhealthalert
93	Can add System Health Metric	24	add_systemhealthmetric
94	Can change System Health Metric	24	change_systemhealthmetric
95	Can delete System Health Metric	24	delete_systemhealthmetric
96	Can view System Health Metric	24	view_systemhealthmetric
97	Can add Backup Schedule	25	add_backupschedule
98	Can change Backup Schedule	25	change_backupschedule
99	Can delete Backup Schedule	25	delete_backupschedule
100	Can view Backup Schedule	25	view_backupschedule
101	Can add Backup Record	26	add_backuprecord
102	Can change Backup Record	26	change_backuprecord
103	Can delete Backup Record	26	delete_backuprecord
104	Can view Backup Record	26	view_backuprecord
105	Can add Backup Integrity Check	27	add_backupintegritycheck
106	Can change Backup Integrity Check	27	change_backupintegritycheck
107	Can delete Backup Integrity Check	27	delete_backupintegritycheck
108	Can view Backup Integrity Check	27	view_backupintegritycheck
109	Can add log entry	28	add_logentry
110	Can change log entry	28	change_logentry
111	Can delete log entry	28	delete_logentry
112	Can view log entry	28	view_logentry
113	Can add User	29	add_user
114	Can change User	29	change_user
115	Can delete User	29	delete_user
116	Can view User	29	view_user
117	Can add System Setting	30	add_systemsettings
118	Can change System Setting	30	change_systemsettings
119	Can delete System Setting	30	delete_systemsettings
120	Can view System Setting	30	view_systemsettings
121	Can add Audit Log	31	add_auditlog
122	Can change Audit Log	31	change_auditlog
123	Can delete Audit Log	31	delete_auditlog
124	Can view Audit Log	31	view_auditlog
125	Can add TOTP Device	32	add_totpdevice
126	Can change TOTP Device	32	change_totpdevice
127	Can delete TOTP Device	32	delete_totpdevice
128	Can view TOTP Device	32	view_totpdevice
129	Can add Security Event	33	add_securityevent
130	Can change Security Event	33	change_securityevent
131	Can delete Security Event	33	delete_securityevent
132	Can view Security Event	33	view_securityevent
133	Can add Rate Limit Attempt	34	add_ratelimitattempt
134	Can change Rate Limit Attempt	34	change_ratelimitattempt
135	Can delete Rate Limit Attempt	34	delete_ratelimitattempt
136	Can view Rate Limit Attempt	34	view_ratelimitattempt
137	Can add Suspicious Activity	35	add_suspiciousactivity
138	Can change Suspicious Activity	35	change_suspiciousactivity
139	Can delete Suspicious Activity	35	delete_suspiciousactivity
140	Can view Suspicious Activity	35	view_suspiciousactivity
141	Can add Notification	36	add_notification
142	Can change Notification	36	change_notification
143	Can delete Notification	36	delete_notification
144	Can view Notification	36	view_notification
145	Can add Notification Delivery Log	37	add_notificationdeliverylog
146	Can change Notification Delivery Log	37	change_notificationdeliverylog
147	Can delete Notification Delivery Log	37	delete_notificationdeliverylog
148	Can view Notification Delivery Log	37	view_notificationdeliverylog
149	Can add Notification Provider	38	add_notificationprovider
150	Can change Notification Provider	38	change_notificationprovider
151	Can delete Notification Provider	38	delete_notificationprovider
152	Can view Notification Provider	38	view_notificationprovider
153	Can add Notification Schedule	39	add_notificationschedule
154	Can change Notification Schedule	39	change_notificationschedule
155	Can delete Notification Schedule	39	delete_notificationschedule
156	Can view Notification Schedule	39	view_notificationschedule
157	Can add Notification Template	40	add_notificationtemplate
158	Can change Notification Template	40	change_notificationtemplate
159	Can delete Notification Template	40	delete_notificationtemplate
160	Can view Notification Template	40	view_notificationtemplate
161	Can add Category	41	add_category
162	Can change Category	41	change_category
163	Can delete Category	41	delete_category
164	Can view Category	41	view_category
165	Can add Gemstone	42	add_gemstone
166	Can change Gemstone	42	change_gemstone
167	Can delete Gemstone	42	delete_gemstone
168	Can view Gemstone	42	view_gemstone
169	Can add Jewelry Item	43	add_jewelryitem
170	Can change Jewelry Item	43	change_jewelryitem
171	Can delete Jewelry Item	43	delete_jewelryitem
172	Can view Jewelry Item	43	view_jewelryitem
173	Can add Jewelry Item Photo	44	add_jewelryitemphoto
174	Can change Jewelry Item Photo	44	change_jewelryitemphoto
175	Can delete Jewelry Item Photo	44	delete_jewelryitemphoto
176	Can view Jewelry Item Photo	44	view_jewelryitemphoto
177	Can add Barcode Generation	45	add_barcodegeneration
178	Can change Barcode Generation	45	change_barcodegeneration
179	Can delete Barcode Generation	45	delete_barcodegeneration
180	Can view Barcode Generation	45	view_barcodegeneration
181	Can add Barcode Settings	46	add_barcodesettings
182	Can change Barcode Settings	46	change_barcodesettings
183	Can delete Barcode Settings	46	delete_barcodesettings
184	Can view Barcode Settings	46	view_barcodesettings
185	Can add Barcode Template	47	add_barcodetemplate
186	Can change Barcode Template	47	change_barcodetemplate
187	Can delete Barcode Template	47	delete_barcodetemplate
188	Can view Barcode Template	47	view_barcodetemplate
189	Can add Barcode Scan History	48	add_barcodescanhistory
190	Can change Barcode Scan History	48	change_barcodescanhistory
191	Can delete Barcode Scan History	48	delete_barcodescanhistory
192	Can view Barcode Scan History	48	view_barcodescanhistory
193	Can add حساب بانکی (Bank Account)	49	add_bankaccount
194	Can change حساب بانکی (Bank Account)	49	change_bankaccount
195	Can delete حساب بانکی (Bank Account)	49	delete_bankaccount
196	Can view حساب بانکی (Bank Account)	49	view_bankaccount
197	Can add حساب (Chart of Account)	50	add_chartofaccounts
198	Can change حساب (Chart of Account)	50	change_chartofaccounts
199	Can delete حساب (Chart of Account)	50	delete_chartofaccounts
200	Can view حساب (Chart of Account)	50	view_chartofaccounts
201	Can add سند حسابداری (Journal Entry)	51	add_journalentry
202	Can change سند حسابداری (Journal Entry)	51	change_journalentry
203	Can delete سند حسابداری (Journal Entry)	51	delete_journalentry
204	Can view سند حسابداری (Journal Entry)	51	view_journalentry
205	Can add ردیف سند (Journal Entry Line)	52	add_journalentryline
206	Can change ردیف سند (Journal Entry Line)	52	change_journalentryline
207	Can delete ردیف سند (Journal Entry Line)	52	delete_journalentryline
208	Can view ردیف سند (Journal Entry Line)	52	view_journalentryline
209	Can add دفتر کل (General Ledger)	53	add_generalledger
210	Can change دفتر کل (General Ledger)	53	change_generalledger
211	Can delete دفتر کل (General Ledger)	53	delete_generalledger
212	Can view دفتر کل (General Ledger)	53	view_generalledger
213	Can add مدیریت چک (Cheque Management)	54	add_chequemanagement
214	Can change مدیریت چک (Cheque Management)	54	change_chequemanagement
215	Can delete مدیریت چک (Cheque Management)	54	delete_chequemanagement
216	Can view مدیریت چک (Cheque Management)	54	view_chequemanagement
217	Can add دفتر معین (Subsidiary Ledger)	55	add_subsidiaryledger
218	Can change دفتر معین (Subsidiary Ledger)	55	change_subsidiaryledger
219	Can delete دفتر معین (Subsidiary Ledger)	55	delete_subsidiaryledger
220	Can view دفتر معین (Subsidiary Ledger)	55	view_subsidiaryledger
221	Can add Customer	56	add_customer
222	Can change Customer	56	change_customer
223	Can delete Customer	56	delete_customer
224	Can view Customer	56	view_customer
225	Can add Customer Note	57	add_customernote
226	Can change Customer Note	57	change_customernote
227	Can delete Customer Note	57	delete_customernote
228	Can view Customer Note	57	view_customernote
229	Can add Loyalty Transaction	58	add_customerloyaltytransaction
230	Can change Loyalty Transaction	58	change_customerloyaltytransaction
231	Can delete Loyalty Transaction	58	delete_customerloyaltytransaction
232	Can view Loyalty Transaction	58	view_customerloyaltytransaction
233	Can add Supplier	59	add_supplier
234	Can change Supplier	59	change_supplier
235	Can delete Supplier	59	delete_supplier
236	Can view Supplier	59	view_supplier
237	Can add Purchase Order	60	add_purchaseorder
238	Can change Purchase Order	60	change_purchaseorder
239	Can delete Purchase Order	60	delete_purchaseorder
240	Can view Purchase Order	60	view_purchaseorder
241	Can add Purchase Order Item	61	add_purchaseorderitem
242	Can change Purchase Order Item	61	change_purchaseorderitem
243	Can delete Purchase Order Item	61	delete_purchaseorderitem
244	Can view Purchase Order Item	61	view_purchaseorderitem
245	Can add Customer Loyalty Program	62	add_customerloyaltyprogram
246	Can change Customer Loyalty Program	62	change_customerloyaltyprogram
247	Can delete Customer Loyalty Program	62	delete_customerloyaltyprogram
248	Can view Customer Loyalty Program	62	view_customerloyaltyprogram
249	Can add Layaway Plan	63	add_layawayplan
250	Can change Layaway Plan	63	change_layawayplan
251	Can delete Layaway Plan	63	delete_layawayplan
252	Can view Layaway Plan	63	view_layawayplan
253	Can add Layaway Reminder	64	add_layawayreminder
254	Can change Layaway Reminder	64	change_layawayreminder
255	Can delete Layaway Reminder	64	delete_layawayreminder
256	Can view Layaway Reminder	64	view_layawayreminder
257	Can add Layaway Refund	65	add_layawayrefund
258	Can change Layaway Refund	65	change_layawayrefund
259	Can delete Layaway Refund	65	delete_layawayrefund
260	Can view Layaway Refund	65	view_layawayrefund
261	Can add Layaway Payment	66	add_layawaypayment
262	Can change Layaway Payment	66	change_layawaypayment
263	Can delete Layaway Payment	66	delete_layawaypayment
264	Can view Layaway Payment	66	view_layawaypayment
265	Can add Layaway Contract	67	add_layawaycontract
266	Can change Layaway Contract	67	change_layawaycontract
267	Can delete Layaway Contract	67	delete_layawaycontract
268	Can view Layaway Contract	67	view_layawaycontract
269	Can add Customer VIP Tier	68	add_customerviptier
270	Can change Customer VIP Tier	68	change_customerviptier
271	Can delete Customer VIP Tier	68	delete_customerviptier
272	Can view Customer VIP Tier	68	view_customerviptier
273	Can add Customer Special Offer	69	add_customerspecialoffer
274	Can change Customer Special Offer	69	change_customerspecialoffer
275	Can delete Customer Special Offer	69	delete_customerspecialoffer
276	Can view Customer Special Offer	69	view_customerspecialoffer
277	Can add Customer Referral	70	add_customerreferral
278	Can change Customer Referral	70	change_customerreferral
279	Can delete Customer Referral	70	delete_customerreferral
280	Can view Customer Referral	70	view_customerreferral
281	Can add Customer Engagement Event	71	add_customerengagementevent
282	Can change Customer Engagement Event	71	change_customerengagementevent
283	Can delete Customer Engagement Event	71	delete_customerengagementevent
284	Can view Customer Engagement Event	71	view_customerengagementevent
285	Can add Scheduled Payment	72	add_layawayscheduledpayment
286	Can change Scheduled Payment	72	change_layawayscheduledpayment
287	Can delete Scheduled Payment	72	delete_layawayscheduledpayment
288	Can view Scheduled Payment	72	view_layawayscheduledpayment
289	Can add Gold Installment Contract	73	add_goldinstallmentcontract
290	Can change Gold Installment Contract	73	change_goldinstallmentcontract
291	Can delete Gold Installment Contract	73	delete_goldinstallmentcontract
292	Can view Gold Installment Contract	73	view_goldinstallmentcontract
293	Can add Gold Weight Adjustment	74	add_goldweightadjustment
294	Can change Gold Weight Adjustment	74	change_goldweightadjustment
295	Can delete Gold Weight Adjustment	74	delete_goldweightadjustment
296	Can view Gold Weight Adjustment	74	view_goldweightadjustment
297	Can add Gold Installment Payment	75	add_goldinstallmentpayment
298	Can change Gold Installment Payment	75	change_goldinstallmentpayment
299	Can delete Gold Installment Payment	75	delete_goldinstallmentpayment
300	Can view Gold Installment Payment	75	view_goldinstallmentpayment
301	Can add POS Transaction	76	add_postransaction
302	Can change POS Transaction	76	change_postransaction
303	Can delete POS Transaction	76	delete_postransaction
304	Can view POS Transaction	76	view_postransaction
305	Can add POS Transaction Line Item	77	add_postransactionlineitem
306	Can change POS Transaction Line Item	77	change_postransactionlineitem
307	Can delete POS Transaction Line Item	77	delete_postransactionlineitem
308	Can view POS Transaction Line Item	77	view_postransactionlineitem
309	Can add POS Offline Storage	78	add_posofflinestorage
310	Can change POS Offline Storage	78	change_posofflinestorage
311	Can delete POS Offline Storage	78	delete_posofflinestorage
312	Can view POS Offline Storage	78	view_posofflinestorage
313	Can add POS Invoice	79	add_posinvoice
314	Can change POS Invoice	79	change_posinvoice
315	Can delete POS Invoice	79	delete_posinvoice
316	Can view POS Invoice	79	view_posinvoice
317	Can add Generated Report	80	add_generatedreport
318	Can change Generated Report	80	change_generatedreport
319	Can delete Generated Report	80	delete_generatedreport
320	Can view Generated Report	80	view_generatedreport
321	Can add Report Template	81	add_reporttemplate
322	Can change Report Template	81	change_reporttemplate
323	Can delete Report Template	81	delete_reporttemplate
324	Can view Report Template	81	view_reporttemplate
325	Can add Report Schedule	82	add_reportschedule
326	Can change Report Schedule	82	change_reportschedule
327	Can delete Report Schedule	82	delete_reportschedule
328	Can view Report Schedule	82	view_reportschedule
329	Can add Report Delivery	83	add_reportdelivery
330	Can change Report Delivery	83	change_reportdelivery
331	Can delete Report Delivery	83	delete_reportdelivery
332	Can view Report Delivery	83	view_reportdelivery
\.


--
-- TOC entry 3751 (class 0 OID 77287)
-- Dependencies: 217
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	auth	permission
2	auth	group
3	contenttypes	contenttype
4	sessions	session
5	db	testmodel
6	tenants	tenant
7	tenants	domain
8	tenants	superadmin
9	tenants	superadminsession
10	tenants	tenantaccesslog
11	tenants	subscriptionplan
12	tenants	billingcycle
13	tenants	tenantinvoice
14	tenants	publicauditlog
15	tenants	publicsecurityevent
16	tenants	publicsuspiciousactivity
17	tenants	publicratelimitattempt
18	admin_panel	impersonationsession
19	admin_panel	backupjob
20	admin_panel	backupschedule
21	admin_panel	restorejob
22	admin_panel	tenantsnapshot
23	admin_panel	systemhealthalert
24	admin_panel	systemhealthmetric
25	system	backupschedule
26	system	backuprecord
27	system	backupintegritycheck
28	admin	logentry
29	core	user
30	core	systemsettings
31	core	auditlog
32	core	totpdevice
33	core	securityevent
34	core	ratelimitattempt
35	core	suspiciousactivity
36	core	notification
37	core	notificationdeliverylog
38	core	notificationprovider
39	core	notificationschedule
40	core	notificationtemplate
41	jewelry	category
42	jewelry	gemstone
43	jewelry	jewelryitem
44	jewelry	jewelryitemphoto
45	jewelry	barcodegeneration
46	jewelry	barcodesettings
47	jewelry	barcodetemplate
48	jewelry	barcodescanhistory
49	accounting	bankaccount
50	accounting	chartofaccounts
51	accounting	journalentry
52	accounting	journalentryline
53	accounting	generalledger
54	accounting	chequemanagement
55	accounting	subsidiaryledger
56	customers	customer
57	customers	customernote
58	customers	customerloyaltytransaction
59	customers	supplier
60	customers	purchaseorder
61	customers	purchaseorderitem
62	customers	customerloyaltyprogram
63	customers	layawayplan
64	customers	layawayreminder
65	customers	layawayrefund
66	customers	layawaypayment
67	customers	layawaycontract
68	customers	customerviptier
69	customers	customerspecialoffer
70	customers	customerreferral
71	customers	customerengagementevent
72	customers	layawayscheduledpayment
73	gold_installments	goldinstallmentcontract
74	gold_installments	goldweightadjustment
75	gold_installments	goldinstallmentpayment
76	pos	postransaction
77	pos	postransactionlineitem
78	pos	posofflinestorage
79	pos	posinvoice
80	reports	generatedreport
81	reports	reporttemplate
82	reports	reportschedule
83	reports	reportdelivery
\.


--
-- TOC entry 3749 (class 0 OID 77279)
-- Dependencies: 215
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2025-09-23 16:00:14.063776+00
2	contenttypes	0002_remove_content_type_name	2025-09-23 16:00:14.109568+00
3	auth	0001_initial	2025-09-23 16:00:15.015688+00
4	auth	0002_alter_permission_name_max_length	2025-09-23 16:00:15.059293+00
5	auth	0003_alter_user_email_max_length	2025-09-23 16:00:15.100385+00
6	auth	0004_alter_user_username_opts	2025-09-23 16:00:15.140921+00
7	auth	0005_alter_user_last_login_null	2025-09-23 16:00:15.191061+00
8	auth	0006_require_contenttypes_0002	2025-09-23 16:00:15.230364+00
9	auth	0007_alter_validators_add_error_messages	2025-09-23 16:00:15.274187+00
10	auth	0008_alter_user_username_max_length	2025-09-23 16:00:15.316569+00
11	auth	0009_alter_user_last_name_max_length	2025-09-23 16:00:15.357938+00
12	auth	0010_alter_group_name_max_length	2025-09-23 16:00:15.404147+00
13	auth	0011_update_proxy_permissions	2025-09-23 16:00:15.449724+00
14	auth	0012_alter_user_first_name_max_length	2025-09-23 16:00:15.491358+00
15	core	0001_initial	2025-09-23 16:00:15.538651+00
16	customers	0001_initial	2025-09-23 16:00:15.630244+00
17	customers	0002_add_purchase_order_models	2025-09-23 16:00:15.770467+00
18	accounting	0001_initial	2025-09-23 16:00:16.394909+00
19	admin	0001_initial	2025-09-23 16:00:16.454671+00
20	admin	0002_logentry_remove_auto_add	2025-09-23 16:00:16.514875+00
21	admin	0003_logentry_add_action_flag_choices	2025-09-23 16:00:16.570829+00
22	admin_panel	0001_initial	2025-09-23 16:00:17.24681+00
23	admin_panel	0002_backupjob_backupschedule_restorejob_and_more	2025-09-23 16:00:18.555182+00
24	admin_panel	0003_alter_restorejob_restore_type_tenantsnapshot	2025-09-23 16:00:19.322572+00
25	admin_panel	0004_systemhealthalert_systemhealthmetric_and_more	2025-09-23 16:00:20.623047+00
26	core	0002_remove_user_tenant_id	2025-09-23 16:00:20.674403+00
27	core	0003_alter_user_managers_user_tenant_schema	2025-09-23 16:00:20.80757+00
28	core	0004_remove_tenant_schema_field	2025-09-23 16:00:20.922379+00
29	core	0005_alter_user_groups_alter_user_role_and_more	2025-09-23 16:00:21.003968+00
30	core	0006_alter_auditlog_action_totpdevice	2025-09-23 16:00:21.079949+00
31	core	0007_security_models_fix	2025-09-23 16:00:21.518323+00
32	core	0008_rename_core_audit__user_id_b8e7b8_idx_core_audit__user_id_da8961_idx_and_more	2025-09-23 16:00:21.873761+00
33	core	0009_backupschedule_backuprecord_backupintegritycheck	2025-09-23 16:00:21.919651+00
34	core	0010_notification_models	2025-09-23 16:00:22.802067+00
35	jewelry	0001_initial	2025-09-23 16:00:23.17059+00
36	customers	0003_customerloyaltyprogram_layawayplan_layawayreminder_and_more	2025-09-23 16:00:24.410691+00
37	health_check_db	0001_initial	2025-09-23 16:00:24.531036+00
38	gold_installments	0001_initial	2025-09-23 16:00:24.936206+00
39	jewelry	0002_add_barcode_models	2025-09-23 16:00:25.347492+00
40	pos	0001_initial	2025-09-23 16:00:26.226002+00
41	pos	0002_remove_posofflinestorage_synced_transaction_and_more	2025-09-23 16:00:27.22076+00
42	reports	0001_initial	2025-09-23 16:00:28.428672+00
43	reports	0002_remove_reportgeneration_created_by_and_more	2025-09-23 16:00:29.026929+00
44	reports	0003_notification_system	2025-09-23 16:00:30.245593+00
45	sessions	0001_initial	2025-09-23 16:00:30.746093+00
46	system	0001_initial	2025-09-23 16:00:32.604457+00
47	tenants	0001_initial	2025-09-23 16:00:33.521316+00
48	tenants	0002_add_superadmin_models	2025-09-23 16:00:35.637403+00
49	tenants	0003_auto_20250919_0321	2025-09-23 16:00:35.72136+00
50	tenants	0004_tenantaccesslog_alter_superadminsession_options_and_more	2025-09-23 16:00:36.688491+00
51	tenants	0005_subscriptionplan_billingcycle_and_more	2025-09-23 16:00:38.946475+00
52	tenants	0006_superadmin_is_2fa_enabled	2025-09-23 16:00:38.993498+00
53	tenants	0007_superadmin_theme_preference	2025-09-23 16:00:39.043793+00
54	tenants	0008_publicauditlog_publicsecurityevent_and_more	2025-09-23 16:00:39.622721+00
55	tenants	0009_publicratelimitattempt	2025-09-23 16:00:39.980354+00
56	db	0001_initial	2025-09-23 16:00:40.026362+00
\.


--
-- TOC entry 3774 (class 0 OID 77455)
-- Dependencies: 240
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
\.


--
-- TOC entry 3773 (class 0 OID 77450)
-- Dependencies: 239
-- Data for Name: health_check_db_testmodel; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.health_check_db_testmodel (id, title) FROM stdin;
\.


--
-- TOC entry 3784 (class 0 OID 77517)
-- Dependencies: 250
-- Data for Name: public.domain; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."public.domain" (id, domain, is_primary, tenant_id) FROM stdin;
1	localhost	t	1
2	admin.localhost	f	1
\.


--
-- TOC entry 3782 (class 0 OID 77507)
-- Dependencies: 248
-- Data for Name: public.tenant; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."public.tenant" (id, schema_name, name, created_on, is_active, owner_name, owner_email, phone_number, address, subscription_plan, subscription_plan_fk_id) FROM stdin;
1	public	Public Schema	2025-09-23	t					basic	\N
\.


--
-- TOC entry 3780 (class 0 OID 77483)
-- Dependencies: 246
-- Data for Name: system_backup_integrity_check; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_backup_integrity_check (id, check_type, status, started_at, completed_at, expected_hash, actual_hash, file_size_verified, error_message, metadata, created_at, backup_record_id) FROM stdin;
\.


--
-- TOC entry 3778 (class 0 OID 77473)
-- Dependencies: 244
-- Data for Name: system_backup_record; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_backup_record (id, backup_id, backup_type, status, frequency, tenant_schema, tenant_domain, file_path, file_size, is_encrypted, encryption_key_hash, file_hash, stored_in_primary, stored_in_secondary, started_at, completed_at, expires_at, metadata, error_message, created_at, updated_at, created_by) FROM stdin;
\.


--
-- TOC entry 3776 (class 0 OID 77465)
-- Dependencies: 242
-- Data for Name: system_backup_schedule; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.system_backup_schedule (id, name, description, schedule_type, frequency, hour, minute, day_of_week, day_of_month, tenant_schema, retention_days, is_active, last_run_at, next_run_at, last_backup_id, total_runs, successful_runs, failed_runs, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 3794 (class 0 OID 77602)
-- Dependencies: 260
-- Data for Name: tenants_access_log; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_access_log (id, user_type, user_id, username, tenant_schema, tenant_name, action, model_name, object_id, details, ip_address, user_agent, request_path, request_method, "timestamp", duration_ms, success, error_message) FROM stdin;
\.


--
-- TOC entry 3798 (class 0 OID 77637)
-- Dependencies: 264
-- Data for Name: tenants_billing_cycle; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_billing_cycle (id, cycle_type, next_billing_date, billing_day, auto_payment_enabled, payment_method, grace_period_days, is_active, created_at, updated_at, tenant_id) FROM stdin;
\.


--
-- TOC entry 3800 (class 0 OID 77652)
-- Dependencies: 266
-- Data for Name: tenants_invoice; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_invoice (id, invoice_number, uuid, issue_date_shamsi, due_date_shamsi, billing_period_start, billing_period_end, subtotal_toman, tax_rate, tax_amount_toman, discount_amount_toman, total_amount_toman, status, payment_method, payment_date_shamsi, payment_reference, bank_name, account_number, iban, line_items, notes, created_at, updated_at, pdf_generated, pdf_file_path, created_by_id, subscription_plan_id, tenant_id) FROM stdin;
\.


--
-- TOC entry 3802 (class 0 OID 77703)
-- Dependencies: 268
-- Data for Name: tenants_publicauditlog; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_publicauditlog (id, action, model_name, object_id, object_repr, changes, ip_address, user_agent, session_key, request_path, request_method, details, created_at) FROM stdin;
\.


--
-- TOC entry 3808 (class 0 OID 77727)
-- Dependencies: 274
-- Data for Name: tenants_publicratelimitattempt; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_publicratelimitattempt (id, identifier, limit_type, endpoint, attempts, window_start, last_attempt, is_blocked, blocked_until, user_agent, details) FROM stdin;
\.


--
-- TOC entry 3804 (class 0 OID 77711)
-- Dependencies: 270
-- Data for Name: tenants_publicsecurityevent; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_publicsecurityevent (id, event_type, severity, username_attempted, ip_address, user_agent, session_key, request_path, request_method, details, is_resolved, resolved_at, resolution_notes, created_at, updated_at) FROM stdin;
1	login_success	low	testadmin	127.0.0.1		hhbsi1oar9n34i412l70s4uo3lenj322	/super-panel/login/	POST	{"user_agent": "", "login_method": "standard"}	f	\N		2025-09-23 16:11:27.39748+00	2025-09-23 16:11:27.397492+00
2	login_success	low	testadmin	127.0.0.1		p9qcwhavc45qlpx2cgkk116ykfwaqbmt	/super-panel/login/	POST	{"user_agent": "", "login_method": "standard"}	f	\N		2025-09-23 16:11:43.698704+00	2025-09-23 16:11:43.698713+00
3	login_success	low	testadmin	127.0.0.1		wbxfmgq0q9cgo1xefaqa4emgepw30yvr	/super-panel/login/	POST	{"user_agent": "", "login_method": "standard"}	f	\N		2025-09-23 16:33:33.465647+00	2025-09-23 16:33:33.465659+00
\.


--
-- TOC entry 3806 (class 0 OID 77719)
-- Dependencies: 272
-- Data for Name: tenants_publicsuspiciousactivity; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_publicsuspiciousactivity (id, activity_type, risk_level, ip_address, user_agent, session_key, pattern_data, confidence_score, is_investigated, investigated_at, investigation_notes, is_false_positive, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 3796 (class 0 OID 77622)
-- Dependencies: 262
-- Data for Name: tenants_subscription_plan; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_subscription_plan (id, name, name_persian, plan_type, monthly_price_toman, yearly_price_toman, max_users, max_inventory_items, max_customers, max_monthly_transactions, max_storage_gb, features, is_active, is_popular, created_at, updated_at, created_by_id) FROM stdin;
\.


--
-- TOC entry 3786 (class 0 OID 77534)
-- Dependencies: 252
-- Data for Name: tenants_superadmin; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_superadmin (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, phone_number, persian_first_name, persian_last_name, created_at, updated_at, can_access_all_data, can_create_tenants, can_suspend_tenants, last_tenant_access, is_2fa_enabled, theme_preference) FROM stdin;
1	argon2$argon2id$v=19$m=102400,t=2,p=8$eklRTXlNNEZtQVRHTTNhbFJQYWxJVg$HZeDUBboA0YaT2N3RYzKpIwdK8wdWRlr1eiH96H0Nc8	2025-09-23 16:33:33.419185+00	t	testadmin			admin@test.com	t	t	2025-09-23 16:01:12.392649+00				2025-09-23 16:01:12.514993+00	2025-09-23 16:01:12.515002+00	t	t	t	\N	f	light
\.


--
-- TOC entry 3788 (class 0 OID 77544)
-- Dependencies: 254
-- Data for Name: tenants_superadmin_groups; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_superadmin_groups (id, superadmin_id, group_id) FROM stdin;
\.


--
-- TOC entry 3792 (class 0 OID 77556)
-- Dependencies: 258
-- Data for Name: tenants_superadmin_session; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_superadmin_session (id, tenant_schema, session_key, ip_address, user_agent, is_active, super_admin_id, access_time) FROM stdin;
\.


--
-- TOC entry 3790 (class 0 OID 77550)
-- Dependencies: 256
-- Data for Name: tenants_superadmin_user_permissions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants_superadmin_user_permissions (id, superadmin_id, permission_id) FROM stdin;
\.


--
-- TOC entry 3814 (class 0 OID 0)
-- Dependencies: 226
-- Name: admin_backup_job_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.admin_backup_job_id_seq', 1, false);


--
-- TOC entry 3815 (class 0 OID 0)
-- Dependencies: 228
-- Name: admin_backup_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.admin_backup_schedule_id_seq', 1, false);


--
-- TOC entry 3816 (class 0 OID 0)
-- Dependencies: 224
-- Name: admin_impersonation_session_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.admin_impersonation_session_id_seq', 1, false);


--
-- TOC entry 3817 (class 0 OID 0)
-- Dependencies: 230
-- Name: admin_restore_job_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.admin_restore_job_id_seq', 1, false);


--
-- TOC entry 3818 (class 0 OID 0)
-- Dependencies: 234
-- Name: admin_system_health_alert_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.admin_system_health_alert_id_seq', 1, false);


--
-- TOC entry 3819 (class 0 OID 0)
-- Dependencies: 236
-- Name: admin_system_health_metric_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.admin_system_health_metric_id_seq', 1, false);


--
-- TOC entry 3820 (class 0 OID 0)
-- Dependencies: 232
-- Name: admin_tenant_snapshot_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.admin_tenant_snapshot_id_seq', 1, false);


--
-- TOC entry 3821 (class 0 OID 0)
-- Dependencies: 220
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- TOC entry 3822 (class 0 OID 0)
-- Dependencies: 222
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- TOC entry 3823 (class 0 OID 0)
-- Dependencies: 218
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 332, true);


--
-- TOC entry 3824 (class 0 OID 0)
-- Dependencies: 216
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 83, true);


--
-- TOC entry 3825 (class 0 OID 0)
-- Dependencies: 214
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 56, true);


--
-- TOC entry 3826 (class 0 OID 0)
-- Dependencies: 238
-- Name: health_check_db_testmodel_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.health_check_db_testmodel_id_seq', 1, false);


--
-- TOC entry 3827 (class 0 OID 0)
-- Dependencies: 249
-- Name: public.domain_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public."public.domain_id_seq"', 2, true);


--
-- TOC entry 3828 (class 0 OID 0)
-- Dependencies: 247
-- Name: public.tenant_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public."public.tenant_id_seq"', 1, true);


--
-- TOC entry 3829 (class 0 OID 0)
-- Dependencies: 245
-- Name: system_backup_integrity_check_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.system_backup_integrity_check_id_seq', 1, false);


--
-- TOC entry 3830 (class 0 OID 0)
-- Dependencies: 243
-- Name: system_backup_record_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.system_backup_record_id_seq', 1, false);


--
-- TOC entry 3831 (class 0 OID 0)
-- Dependencies: 241
-- Name: system_backup_schedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.system_backup_schedule_id_seq', 1, false);


--
-- TOC entry 3832 (class 0 OID 0)
-- Dependencies: 259
-- Name: tenants_access_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_access_log_id_seq', 1, false);


--
-- TOC entry 3833 (class 0 OID 0)
-- Dependencies: 263
-- Name: tenants_billing_cycle_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_billing_cycle_id_seq', 1, false);


--
-- TOC entry 3834 (class 0 OID 0)
-- Dependencies: 265
-- Name: tenants_invoice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_invoice_id_seq', 1, false);


--
-- TOC entry 3835 (class 0 OID 0)
-- Dependencies: 267
-- Name: tenants_publicauditlog_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_publicauditlog_id_seq', 1, false);


--
-- TOC entry 3836 (class 0 OID 0)
-- Dependencies: 273
-- Name: tenants_publicratelimitattempt_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_publicratelimitattempt_id_seq', 1, false);


--
-- TOC entry 3837 (class 0 OID 0)
-- Dependencies: 269
-- Name: tenants_publicsecurityevent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_publicsecurityevent_id_seq', 3, true);


--
-- TOC entry 3838 (class 0 OID 0)
-- Dependencies: 271
-- Name: tenants_publicsuspiciousactivity_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_publicsuspiciousactivity_id_seq', 1, false);


--
-- TOC entry 3839 (class 0 OID 0)
-- Dependencies: 261
-- Name: tenants_subscription_plan_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_subscription_plan_id_seq', 1, false);


--
-- TOC entry 3840 (class 0 OID 0)
-- Dependencies: 253
-- Name: tenants_superadmin_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_superadmin_groups_id_seq', 1, false);


--
-- TOC entry 3841 (class 0 OID 0)
-- Dependencies: 251
-- Name: tenants_superadmin_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_superadmin_id_seq', 1, true);


--
-- TOC entry 3842 (class 0 OID 0)
-- Dependencies: 257
-- Name: tenants_superadmin_session_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_superadmin_session_id_seq', 1, false);


--
-- TOC entry 3843 (class 0 OID 0)
-- Dependencies: 255
-- Name: tenants_superadmin_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tenants_superadmin_user_permissions_id_seq', 1, false);


--
-- TOC entry 3459 (class 2606 OID 77365)
-- Name: admin_backup_job admin_backup_job_job_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_backup_job
    ADD CONSTRAINT admin_backup_job_job_id_key UNIQUE (job_id);


--
-- TOC entry 3461 (class 2606 OID 77363)
-- Name: admin_backup_job admin_backup_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_backup_job
    ADD CONSTRAINT admin_backup_job_pkey PRIMARY KEY (id);


--
-- TOC entry 3463 (class 2606 OID 77375)
-- Name: admin_backup_schedule admin_backup_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_backup_schedule
    ADD CONSTRAINT admin_backup_schedule_pkey PRIMARY KEY (id);


--
-- TOC entry 3451 (class 2606 OID 77347)
-- Name: admin_impersonation_session admin_impersonation_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_impersonation_session
    ADD CONSTRAINT admin_impersonation_session_pkey PRIMARY KEY (id);


--
-- TOC entry 3453 (class 2606 OID 77349)
-- Name: admin_impersonation_session admin_impersonation_session_session_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_impersonation_session
    ADD CONSTRAINT admin_impersonation_session_session_id_key UNIQUE (session_id);


--
-- TOC entry 3465 (class 2606 OID 77386)
-- Name: admin_restore_job admin_restore_job_job_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_restore_job
    ADD CONSTRAINT admin_restore_job_job_id_key UNIQUE (job_id);


--
-- TOC entry 3467 (class 2606 OID 77384)
-- Name: admin_restore_job admin_restore_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_restore_job
    ADD CONSTRAINT admin_restore_job_pkey PRIMARY KEY (id);


--
-- TOC entry 3477 (class 2606 OID 77428)
-- Name: admin_system_health_alert admin_system_health_alert_alert_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_system_health_alert
    ADD CONSTRAINT admin_system_health_alert_alert_id_key UNIQUE (alert_id);


--
-- TOC entry 3479 (class 2606 OID 77426)
-- Name: admin_system_health_alert admin_system_health_alert_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_system_health_alert
    ADD CONSTRAINT admin_system_health_alert_pkey PRIMARY KEY (id);


--
-- TOC entry 3484 (class 2606 OID 77436)
-- Name: admin_system_health_metric admin_system_health_metric_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_system_health_metric
    ADD CONSTRAINT admin_system_health_metric_pkey PRIMARY KEY (id);


--
-- TOC entry 3470 (class 2606 OID 77405)
-- Name: admin_tenant_snapshot admin_tenant_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_tenant_snapshot
    ADD CONSTRAINT admin_tenant_snapshot_pkey PRIMARY KEY (id);


--
-- TOC entry 3472 (class 2606 OID 77407)
-- Name: admin_tenant_snapshot admin_tenant_snapshot_snapshot_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_tenant_snapshot
    ADD CONSTRAINT admin_tenant_snapshot_snapshot_id_key UNIQUE (snapshot_id);


--
-- TOC entry 3436 (class 2606 OID 77338)
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- TOC entry 3441 (class 2606 OID 77324)
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- TOC entry 3444 (class 2606 OID 77313)
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 3438 (class 2606 OID 77305)
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- TOC entry 3431 (class 2606 OID 77315)
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- TOC entry 3433 (class 2606 OID 77299)
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- TOC entry 3426 (class 2606 OID 77293)
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- TOC entry 3428 (class 2606 OID 77291)
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- TOC entry 3424 (class 2606 OID 77285)
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- TOC entry 3489 (class 2606 OID 77461)
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- TOC entry 3486 (class 2606 OID 77454)
-- Name: health_check_db_testmodel health_check_db_testmodel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.health_check_db_testmodel
    ADD CONSTRAINT health_check_db_testmodel_pkey PRIMARY KEY (id);


--
-- TOC entry 3518 (class 2606 OID 77523)
-- Name: public.domain public.domain_domain_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."public.domain"
    ADD CONSTRAINT "public.domain_domain_key" UNIQUE (domain);


--
-- TOC entry 3521 (class 2606 OID 77521)
-- Name: public.domain public.domain_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."public.domain"
    ADD CONSTRAINT "public.domain_pkey" PRIMARY KEY (id);


--
-- TOC entry 3511 (class 2606 OID 77513)
-- Name: public.tenant public.tenant_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."public.tenant"
    ADD CONSTRAINT "public.tenant_pkey" PRIMARY KEY (id);


--
-- TOC entry 3514 (class 2606 OID 77515)
-- Name: public.tenant public.tenant_schema_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."public.tenant"
    ADD CONSTRAINT "public.tenant_schema_name_key" UNIQUE (schema_name);


--
-- TOC entry 3509 (class 2606 OID 77489)
-- Name: system_backup_integrity_check system_backup_integrity_check_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_backup_integrity_check
    ADD CONSTRAINT system_backup_integrity_check_pkey PRIMARY KEY (id);


--
-- TOC entry 3502 (class 2606 OID 77481)
-- Name: system_backup_record system_backup_record_backup_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_backup_record
    ADD CONSTRAINT system_backup_record_backup_id_key UNIQUE (backup_id);


--
-- TOC entry 3504 (class 2606 OID 77479)
-- Name: system_backup_record system_backup_record_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_backup_record
    ADD CONSTRAINT system_backup_record_pkey PRIMARY KEY (id);


--
-- TOC entry 3495 (class 2606 OID 77471)
-- Name: system_backup_schedule system_backup_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_backup_schedule
    ADD CONSTRAINT system_backup_schedule_pkey PRIMARY KEY (id);


--
-- TOC entry 3552 (class 2606 OID 77610)
-- Name: tenants_access_log tenants_access_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_access_log
    ADD CONSTRAINT tenants_access_log_pkey PRIMARY KEY (id);


--
-- TOC entry 3560 (class 2606 OID 77643)
-- Name: tenants_billing_cycle tenants_billing_cycle_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_billing_cycle
    ADD CONSTRAINT tenants_billing_cycle_pkey PRIMARY KEY (id);


--
-- TOC entry 3562 (class 2606 OID 77645)
-- Name: tenants_billing_cycle tenants_billing_cycle_tenant_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_billing_cycle
    ADD CONSTRAINT tenants_billing_cycle_tenant_id_key UNIQUE (tenant_id);


--
-- TOC entry 3571 (class 2606 OID 77660)
-- Name: tenants_invoice tenants_invoice_invoice_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_invoice
    ADD CONSTRAINT tenants_invoice_invoice_number_key UNIQUE (invoice_number);


--
-- TOC entry 3573 (class 2606 OID 77658)
-- Name: tenants_invoice tenants_invoice_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_invoice
    ADD CONSTRAINT tenants_invoice_pkey PRIMARY KEY (id);


--
-- TOC entry 3577 (class 2606 OID 77662)
-- Name: tenants_invoice tenants_invoice_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_invoice
    ADD CONSTRAINT tenants_invoice_uuid_key UNIQUE (uuid);


--
-- TOC entry 3579 (class 2606 OID 77709)
-- Name: tenants_publicauditlog tenants_publicauditlog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_publicauditlog
    ADD CONSTRAINT tenants_publicauditlog_pkey PRIMARY KEY (id);


--
-- TOC entry 3585 (class 2606 OID 77736)
-- Name: tenants_publicratelimitattempt tenants_publicratelimita_identifier_limit_type_en_fb09cf82_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_publicratelimitattempt
    ADD CONSTRAINT tenants_publicratelimita_identifier_limit_type_en_fb09cf82_uniq UNIQUE (identifier, limit_type, endpoint);


--
-- TOC entry 3587 (class 2606 OID 77734)
-- Name: tenants_publicratelimitattempt tenants_publicratelimitattempt_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_publicratelimitattempt
    ADD CONSTRAINT tenants_publicratelimitattempt_pkey PRIMARY KEY (id);


--
-- TOC entry 3581 (class 2606 OID 77717)
-- Name: tenants_publicsecurityevent tenants_publicsecurityevent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_publicsecurityevent
    ADD CONSTRAINT tenants_publicsecurityevent_pkey PRIMARY KEY (id);


--
-- TOC entry 3583 (class 2606 OID 77725)
-- Name: tenants_publicsuspiciousactivity tenants_publicsuspiciousactivity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_publicsuspiciousactivity
    ADD CONSTRAINT tenants_publicsuspiciousactivity_pkey PRIMARY KEY (id);


--
-- TOC entry 3555 (class 2606 OID 77633)
-- Name: tenants_subscription_plan tenants_subscription_plan_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_subscription_plan
    ADD CONSTRAINT tenants_subscription_plan_pkey PRIMARY KEY (id);


--
-- TOC entry 3558 (class 2606 OID 77635)
-- Name: tenants_subscription_plan tenants_subscription_plan_plan_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_subscription_plan
    ADD CONSTRAINT tenants_subscription_plan_plan_type_key UNIQUE (plan_type);


--
-- TOC entry 3530 (class 2606 OID 77548)
-- Name: tenants_superadmin_groups tenants_superadmin_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_groups
    ADD CONSTRAINT tenants_superadmin_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 3533 (class 2606 OID 77565)
-- Name: tenants_superadmin_groups tenants_superadmin_groups_superadmin_id_group_id_006b168b_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_groups
    ADD CONSTRAINT tenants_superadmin_groups_superadmin_id_group_id_006b168b_uniq UNIQUE (superadmin_id, group_id);


--
-- TOC entry 3524 (class 2606 OID 77540)
-- Name: tenants_superadmin tenants_superadmin_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin
    ADD CONSTRAINT tenants_superadmin_pkey PRIMARY KEY (id);


--
-- TOC entry 3544 (class 2606 OID 77562)
-- Name: tenants_superadmin_session tenants_superadmin_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_session
    ADD CONSTRAINT tenants_superadmin_session_pkey PRIMARY KEY (id);


--
-- TOC entry 3535 (class 2606 OID 77579)
-- Name: tenants_superadmin_user_permissions tenants_superadmin_user__superadmin_id_permission_283d3791_uniq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_user_permissions
    ADD CONSTRAINT tenants_superadmin_user__superadmin_id_permission_283d3791_uniq UNIQUE (superadmin_id, permission_id);


--
-- TOC entry 3538 (class 2606 OID 77554)
-- Name: tenants_superadmin_user_permissions tenants_superadmin_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_user_permissions
    ADD CONSTRAINT tenants_superadmin_user_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 3527 (class 2606 OID 77542)
-- Name: tenants_superadmin tenants_superadmin_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin
    ADD CONSTRAINT tenants_superadmin_username_key UNIQUE (username);


--
-- TOC entry 3454 (class 1259 OID 77388)
-- Name: admin_backu_backup__9fc395_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_backu_backup__9fc395_idx ON public.admin_backup_job USING btree (backup_type, status);


--
-- TOC entry 3455 (class 1259 OID 77389)
-- Name: admin_backu_frequen_372e7d_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_backu_frequen_372e7d_idx ON public.admin_backup_job USING btree (frequency, next_run);


--
-- TOC entry 3456 (class 1259 OID 77390)
-- Name: admin_backu_job_id_f88ddd_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_backu_job_id_f88ddd_idx ON public.admin_backup_job USING btree (job_id);


--
-- TOC entry 3457 (class 1259 OID 77387)
-- Name: admin_backu_status_ed96bd_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_backu_status_ed96bd_idx ON public.admin_backup_job USING btree (status, created_at);


--
-- TOC entry 3445 (class 1259 OID 77350)
-- Name: admin_imper_admin_u_6ae6b4_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_imper_admin_u_6ae6b4_idx ON public.admin_impersonation_session USING btree (admin_user_id, start_time);


--
-- TOC entry 3446 (class 1259 OID 77354)
-- Name: admin_imper_session_194767_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_imper_session_194767_idx ON public.admin_impersonation_session USING btree (session_id);


--
-- TOC entry 3447 (class 1259 OID 77353)
-- Name: admin_imper_status_307a89_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_imper_status_307a89_idx ON public.admin_impersonation_session USING btree (status, start_time);


--
-- TOC entry 3448 (class 1259 OID 77351)
-- Name: admin_imper_target__ed8738_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_imper_target__ed8738_idx ON public.admin_impersonation_session USING btree (target_user_id, start_time);


--
-- TOC entry 3449 (class 1259 OID 77352)
-- Name: admin_imper_tenant__e3a00e_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_imper_tenant__e3a00e_idx ON public.admin_impersonation_session USING btree (tenant_schema, start_time);


--
-- TOC entry 3468 (class 1259 OID 77396)
-- Name: admin_restore_job_source_backup_id_19894d4b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_restore_job_source_backup_id_19894d4b ON public.admin_restore_job USING btree (source_backup_id);


--
-- TOC entry 3473 (class 1259 OID 77447)
-- Name: admin_syste_alert_i_5c9e56_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_syste_alert_i_5c9e56_idx ON public.admin_system_health_alert USING btree (alert_id);


--
-- TOC entry 3474 (class 1259 OID 77446)
-- Name: admin_syste_categor_690516_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_syste_categor_690516_idx ON public.admin_system_health_alert USING btree (category, status);


--
-- TOC entry 3481 (class 1259 OID 77438)
-- Name: admin_syste_metric__27aa60_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_syste_metric__27aa60_idx ON public.admin_system_health_metric USING btree (metric_type, "timestamp");


--
-- TOC entry 3475 (class 1259 OID 77445)
-- Name: admin_syste_status_de3753_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_syste_status_de3753_idx ON public.admin_system_health_alert USING btree (status, severity, created_at);


--
-- TOC entry 3482 (class 1259 OID 77439)
-- Name: admin_syste_timesta_b8e39b_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_syste_timesta_b8e39b_idx ON public.admin_system_health_metric USING btree ("timestamp");


--
-- TOC entry 3480 (class 1259 OID 77448)
-- Name: admin_system_health_alert_source_metric_id_20da84e8; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX admin_system_health_alert_source_metric_id_20da84e8 ON public.admin_system_health_alert USING btree (source_metric_id);


--
-- TOC entry 3434 (class 1259 OID 77339)
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- TOC entry 3439 (class 1259 OID 77335)
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- TOC entry 3442 (class 1259 OID 77336)
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- TOC entry 3429 (class 1259 OID 77321)
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- TOC entry 3487 (class 1259 OID 77463)
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- TOC entry 3490 (class 1259 OID 77462)
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- TOC entry 3516 (class 1259 OID 77530)
-- Name: public.domain_domain_bb0b26a4_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "public.domain_domain_bb0b26a4_like" ON public."public.domain" USING btree (domain varchar_pattern_ops);


--
-- TOC entry 3519 (class 1259 OID 77531)
-- Name: public.domain_is_primary_55af10c7; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "public.domain_is_primary_55af10c7" ON public."public.domain" USING btree (is_primary);


--
-- TOC entry 3522 (class 1259 OID 77532)
-- Name: public.domain_tenant_id_da447c7f; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "public.domain_tenant_id_da447c7f" ON public."public.domain" USING btree (tenant_id);


--
-- TOC entry 3512 (class 1259 OID 77524)
-- Name: public.tenant_schema_name_20c2de3c_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "public.tenant_schema_name_20c2de3c_like" ON public."public.tenant" USING btree (schema_name varchar_pattern_ops);


--
-- TOC entry 3515 (class 1259 OID 77675)
-- Name: public.tenant_subscription_plan_fk_id_7207af8b; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX "public.tenant_subscription_plan_fk_id_7207af8b" ON public."public.tenant" USING btree (subscription_plan_fk_id);


--
-- TOC entry 3496 (class 1259 OID 77494)
-- Name: system_back_backup__2bea12_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_backup__2bea12_idx ON public.system_backup_record USING btree (backup_type, status);


--
-- TOC entry 3505 (class 1259 OID 77504)
-- Name: system_back_backup__fe79b2_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_backup__fe79b2_idx ON public.system_backup_integrity_check USING btree (backup_record_id, status);


--
-- TOC entry 3497 (class 1259 OID 77496)
-- Name: system_back_created_2959e5_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_created_2959e5_idx ON public.system_backup_record USING btree (created_at);


--
-- TOC entry 3506 (class 1259 OID 77505)
-- Name: system_back_created_8f1a80_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_created_8f1a80_idx ON public.system_backup_integrity_check USING btree (created_at);


--
-- TOC entry 3498 (class 1259 OID 77497)
-- Name: system_back_expires_09de72_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_expires_09de72_idx ON public.system_backup_record USING btree (expires_at);


--
-- TOC entry 3491 (class 1259 OID 77490)
-- Name: system_back_is_acti_c8cf8a_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_is_acti_c8cf8a_idx ON public.system_backup_schedule USING btree (is_active, next_run_at);


--
-- TOC entry 3492 (class 1259 OID 77491)
-- Name: system_back_schedul_a17780_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_schedul_a17780_idx ON public.system_backup_schedule USING btree (schedule_type);


--
-- TOC entry 3499 (class 1259 OID 77495)
-- Name: system_back_tenant__1aa49f_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_tenant__1aa49f_idx ON public.system_backup_record USING btree (tenant_schema);


--
-- TOC entry 3493 (class 1259 OID 77492)
-- Name: system_back_tenant__4eb251_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_back_tenant__4eb251_idx ON public.system_backup_schedule USING btree (tenant_schema);


--
-- TOC entry 3507 (class 1259 OID 77503)
-- Name: system_backup_integrity_check_backup_record_id_6d7e1dd4; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_backup_integrity_check_backup_record_id_6d7e1dd4 ON public.system_backup_integrity_check USING btree (backup_record_id);


--
-- TOC entry 3500 (class 1259 OID 77493)
-- Name: system_backup_record_backup_id_37386484_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX system_backup_record_backup_id_37386484_like ON public.system_backup_record USING btree (backup_id varchar_pattern_ops);


--
-- TOC entry 3546 (class 1259 OID 77618)
-- Name: tenants_acc_action_3be01c_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_acc_action_3be01c_idx ON public.tenants_access_log USING btree (action);


--
-- TOC entry 3547 (class 1259 OID 77620)
-- Name: tenants_acc_success_6b5fea_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_acc_success_6b5fea_idx ON public.tenants_access_log USING btree (success);


--
-- TOC entry 3548 (class 1259 OID 77617)
-- Name: tenants_acc_tenant__351b58_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_acc_tenant__351b58_idx ON public.tenants_access_log USING btree (tenant_schema);


--
-- TOC entry 3549 (class 1259 OID 77619)
-- Name: tenants_acc_timesta_281aad_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_acc_timesta_281aad_idx ON public.tenants_access_log USING btree ("timestamp");


--
-- TOC entry 3550 (class 1259 OID 77616)
-- Name: tenants_acc_user_ty_85334c_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_acc_user_ty_85334c_idx ON public.tenants_access_log USING btree (user_type, user_id);


--
-- TOC entry 3563 (class 1259 OID 77698)
-- Name: tenants_inv_due_dat_964485_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_inv_due_dat_964485_idx ON public.tenants_invoice USING btree (due_date_shamsi);


--
-- TOC entry 3564 (class 1259 OID 77696)
-- Name: tenants_inv_invoice_b03261_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_inv_invoice_b03261_idx ON public.tenants_invoice USING btree (invoice_number);


--
-- TOC entry 3565 (class 1259 OID 77697)
-- Name: tenants_inv_issue_d_412371_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_inv_issue_d_412371_idx ON public.tenants_invoice USING btree (issue_date_shamsi);


--
-- TOC entry 3566 (class 1259 OID 77699)
-- Name: tenants_inv_status_8ea065_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_inv_status_8ea065_idx ON public.tenants_invoice USING btree (status);


--
-- TOC entry 3567 (class 1259 OID 77695)
-- Name: tenants_inv_tenant__50abd5_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_inv_tenant__50abd5_idx ON public.tenants_invoice USING btree (tenant_id, status);


--
-- TOC entry 3568 (class 1259 OID 77692)
-- Name: tenants_invoice_created_by_id_3443cc12; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_invoice_created_by_id_3443cc12 ON public.tenants_invoice USING btree (created_by_id);


--
-- TOC entry 3569 (class 1259 OID 77691)
-- Name: tenants_invoice_invoice_number_5e928b09_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_invoice_invoice_number_5e928b09_like ON public.tenants_invoice USING btree (invoice_number varchar_pattern_ops);


--
-- TOC entry 3574 (class 1259 OID 77693)
-- Name: tenants_invoice_subscription_plan_id_a1e39206; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_invoice_subscription_plan_id_a1e39206 ON public.tenants_invoice USING btree (subscription_plan_id);


--
-- TOC entry 3575 (class 1259 OID 77694)
-- Name: tenants_invoice_tenant_id_53aea1c2; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_invoice_tenant_id_53aea1c2 ON public.tenants_invoice USING btree (tenant_id);


--
-- TOC entry 3553 (class 1259 OID 77669)
-- Name: tenants_subscription_plan_created_by_id_34ba6c8d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_subscription_plan_created_by_id_34ba6c8d ON public.tenants_subscription_plan USING btree (created_by_id);


--
-- TOC entry 3556 (class 1259 OID 77668)
-- Name: tenants_subscription_plan_plan_type_db3273fc_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_subscription_plan_plan_type_db3273fc_like ON public.tenants_subscription_plan USING btree (plan_type varchar_pattern_ops);


--
-- TOC entry 3540 (class 1259 OID 77615)
-- Name: tenants_sup_access__c786cc_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_sup_access__c786cc_idx ON public.tenants_superadmin_session USING btree (access_time);


--
-- TOC entry 3541 (class 1259 OID 77599)
-- Name: tenants_sup_session_d92be0_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_sup_session_d92be0_idx ON public.tenants_superadmin_session USING btree (session_key);


--
-- TOC entry 3542 (class 1259 OID 77598)
-- Name: tenants_sup_super_a_9440fa_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_sup_super_a_9440fa_idx ON public.tenants_superadmin_session USING btree (super_admin_id, tenant_schema);


--
-- TOC entry 3528 (class 1259 OID 77577)
-- Name: tenants_superadmin_groups_group_id_de91425d; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_superadmin_groups_group_id_de91425d ON public.tenants_superadmin_groups USING btree (group_id);


--
-- TOC entry 3531 (class 1259 OID 77576)
-- Name: tenants_superadmin_groups_superadmin_id_e2577514; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_superadmin_groups_superadmin_id_e2577514 ON public.tenants_superadmin_groups USING btree (superadmin_id);


--
-- TOC entry 3545 (class 1259 OID 77597)
-- Name: tenants_superadmin_session_super_admin_id_2172b352; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_superadmin_session_super_admin_id_2172b352 ON public.tenants_superadmin_session USING btree (super_admin_id);


--
-- TOC entry 3536 (class 1259 OID 77591)
-- Name: tenants_superadmin_user_permissions_permission_id_bac6c7f5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_superadmin_user_permissions_permission_id_bac6c7f5 ON public.tenants_superadmin_user_permissions USING btree (permission_id);


--
-- TOC entry 3539 (class 1259 OID 77590)
-- Name: tenants_superadmin_user_permissions_superadmin_id_4657e0c5; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_superadmin_user_permissions_superadmin_id_4657e0c5 ON public.tenants_superadmin_user_permissions USING btree (superadmin_id);


--
-- TOC entry 3525 (class 1259 OID 77563)
-- Name: tenants_superadmin_username_8b8428ab_like; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tenants_superadmin_username_8b8428ab_like ON public.tenants_superadmin USING btree (username varchar_pattern_ops);


--
-- TOC entry 3591 (class 2606 OID 77391)
-- Name: admin_restore_job admin_restore_job_source_backup_id_19894d4b_fk_admin_bac; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_restore_job
    ADD CONSTRAINT admin_restore_job_source_backup_id_19894d4b_fk_admin_bac FOREIGN KEY (source_backup_id) REFERENCES public.admin_backup_job(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3592 (class 2606 OID 77440)
-- Name: admin_system_health_alert admin_system_health__source_metric_id_20da84e8_fk_admin_sys; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_system_health_alert
    ADD CONSTRAINT admin_system_health__source_metric_id_20da84e8_fk_admin_sys FOREIGN KEY (source_metric_id) REFERENCES public.admin_system_health_metric(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3589 (class 2606 OID 77330)
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3590 (class 2606 OID 77325)
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3588 (class 2606 OID 77316)
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3595 (class 2606 OID 77525)
-- Name: public.domain public.domain_tenant_id_da447c7f_fk_public.tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."public.domain"
    ADD CONSTRAINT "public.domain_tenant_id_da447c7f_fk_public.tenant_id" FOREIGN KEY (tenant_id) REFERENCES public."public.tenant"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3594 (class 2606 OID 77646)
-- Name: public.tenant public.tenant_subscription_plan_fk_7207af8b_fk_tenants_s; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."public.tenant"
    ADD CONSTRAINT "public.tenant_subscription_plan_fk_7207af8b_fk_tenants_s" FOREIGN KEY (subscription_plan_fk_id) REFERENCES public.tenants_subscription_plan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3593 (class 2606 OID 77498)
-- Name: system_backup_integrity_check system_backup_integr_backup_record_id_6d7e1dd4_fk_system_ba; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_backup_integrity_check
    ADD CONSTRAINT system_backup_integr_backup_record_id_6d7e1dd4_fk_system_ba FOREIGN KEY (backup_record_id) REFERENCES public.system_backup_record(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3602 (class 2606 OID 77670)
-- Name: tenants_billing_cycle tenants_billing_cycle_tenant_id_12cd2f33_fk_public.tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_billing_cycle
    ADD CONSTRAINT "tenants_billing_cycle_tenant_id_12cd2f33_fk_public.tenant_id" FOREIGN KEY (tenant_id) REFERENCES public."public.tenant"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3603 (class 2606 OID 77676)
-- Name: tenants_invoice tenants_invoice_created_by_id_3443cc12_fk_tenants_superadmin_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_invoice
    ADD CONSTRAINT tenants_invoice_created_by_id_3443cc12_fk_tenants_superadmin_id FOREIGN KEY (created_by_id) REFERENCES public.tenants_superadmin(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3604 (class 2606 OID 77681)
-- Name: tenants_invoice tenants_invoice_subscription_plan_id_a1e39206_fk_tenants_s; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_invoice
    ADD CONSTRAINT tenants_invoice_subscription_plan_id_a1e39206_fk_tenants_s FOREIGN KEY (subscription_plan_id) REFERENCES public.tenants_subscription_plan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3605 (class 2606 OID 77686)
-- Name: tenants_invoice tenants_invoice_tenant_id_53aea1c2_fk_public.tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_invoice
    ADD CONSTRAINT "tenants_invoice_tenant_id_53aea1c2_fk_public.tenant_id" FOREIGN KEY (tenant_id) REFERENCES public."public.tenant"(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3601 (class 2606 OID 77663)
-- Name: tenants_subscription_plan tenants_subscription_created_by_id_34ba6c8d_fk_tenants_s; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_subscription_plan
    ADD CONSTRAINT tenants_subscription_created_by_id_34ba6c8d_fk_tenants_s FOREIGN KEY (created_by_id) REFERENCES public.tenants_superadmin(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3596 (class 2606 OID 77566)
-- Name: tenants_superadmin_groups tenants_superadmin_g_superadmin_id_e2577514_fk_tenants_s; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_groups
    ADD CONSTRAINT tenants_superadmin_g_superadmin_id_e2577514_fk_tenants_s FOREIGN KEY (superadmin_id) REFERENCES public.tenants_superadmin(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3597 (class 2606 OID 77571)
-- Name: tenants_superadmin_groups tenants_superadmin_groups_group_id_de91425d_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_groups
    ADD CONSTRAINT tenants_superadmin_groups_group_id_de91425d_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3600 (class 2606 OID 77592)
-- Name: tenants_superadmin_session tenants_superadmin_s_super_admin_id_2172b352_fk_tenants_s; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_session
    ADD CONSTRAINT tenants_superadmin_s_super_admin_id_2172b352_fk_tenants_s FOREIGN KEY (super_admin_id) REFERENCES public.tenants_superadmin(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3598 (class 2606 OID 77585)
-- Name: tenants_superadmin_user_permissions tenants_superadmin_u_permission_id_bac6c7f5_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_user_permissions
    ADD CONSTRAINT tenants_superadmin_u_permission_id_bac6c7f5_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3599 (class 2606 OID 77580)
-- Name: tenants_superadmin_user_permissions tenants_superadmin_u_superadmin_id_4657e0c5_fk_tenants_s; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants_superadmin_user_permissions
    ADD CONSTRAINT tenants_superadmin_u_superadmin_id_4657e0c5_fk_tenants_s FOREIGN KEY (superadmin_id) REFERENCES public.tenants_superadmin(id) DEFERRABLE INITIALLY DEFERRED;


-- Completed on 2025-09-23 20:23:06 +0330

--
-- PostgreSQL database dump complete
--

\unrestrict 3p3GDa4a9zs7KuNBDTqaxELKCf5g4ZoQ7lO5Cxc8ATJFme6kOUu9DH6ZG9MlLBm

