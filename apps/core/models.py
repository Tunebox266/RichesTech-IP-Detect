# core/models.py
from django.db import models
from django.contrib.auth import get_user_model
from ckeditor.fields import RichTextField
from django.utils import timezone

User = get_user_model()

class AcademicSetting(models.Model):
    SEMESTER_CHOICES = (
        (1, 'First Semester'),
        (2, 'Second Semester'),
    )
    
    academic_year = models.CharField(max_length=9, help_text="e.g., 2023/2024")
    current_semester = models.IntegerField(choices=SEMESTER_CHOICES, default=1)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['academic_year', 'current_semester']
    
    def __str__(self):
        return f"{self.academic_year} - Semester {self.current_semester}"
    
    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all other academic settings
            AcademicSetting.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class Announcement(models.Model):
  
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
     ]
    
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    content = RichTextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    target_groups = models .CharField(
     max_length=50,
     choices=[
        ('student','Student'),
       # ('executive', 'Excutive')
        ('admin','Admin'),
      #  ('staff', 'Staff')
        ('all','All')
      ],
     default='all'
    )
        # Attachment
    attachment = models.FileField(
        upload_to='announcements/',
        null=True,
        blank=True,
        help_text='Attach file to announcement'
    )
    
    is_pinned = models.BooleanField(default=False)
    
    is_archived = models.BooleanField(default=False)
    
    # Image
    image = models.ImageField(
        upload_to='announcements/images/',
        null=True,
        blank=True,
        help_text='Featured image for announcement'
    )
    
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=2
    )
    
    expiry_date = models.DateTimeField(null=True, blank=True)  # ADD THIS
    
    views = models.PositiveIntegerField(default=0, help_text="Number of times this announcement was viewed")

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

class AnnouncementComment(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}"

class AnnouncementCommentReply(models.Model):
    comment = models.ForeignKey(
        'AnnouncementComment', 
        on_delete=models.CASCADE, 
        related_name='replies'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}"


# apps/core/models.py

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('danger', 'Danger'),
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default='info')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_notifications')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_global = models.BooleanField(default=False)
    target_users = models.ManyToManyField(User, related_name='core_notifications', blank=True)
    read_by = models.ManyToManyField(User, blank=True, related_name="read_notifications")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def mark_as_read(self, user):
        """Mark notification as read by a user"""
        if user not in self.read_by.all():
            self.read_by.add(user)
    
    def is_read_by(self, user):
        """Check if notification is read by a user"""
        return self.read_by.filter(id=user.id).exists()

# apps/core/models.py

class AnnouncementLike(models.Model):
    """Model for tracking announcement likes"""
    announcement = models.ForeignKey('Announcement', on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcement_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['announcement', 'user']  # Prevent duplicate likes
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} liked {self.announcement.title}"


class EmailSubscription(models.Model):
    """Model for email newsletter subscriptions"""
    FREQUENCY_CHOICES = (
        ('instant', 'Instant'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest'),
        ('never', 'Never'),
    )
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    
    # Subscription preferences
    is_active = models.BooleanField(default=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='instant')
    
    # What to subscribe to
    subscribe_announcements = models.BooleanField(default=True)
    subscribe_events = models.BooleanField(default=True)
    subscribe_blog = models.BooleanField(default=False)
    
    # Metadata
    verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    unsubscribed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email


class SubscriptionLog(models.Model):
    """Log subscription activities"""
    ACTION_CHOICES = (
        ('subscribe', 'Subscribed'),
        ('unsubscribe', 'Unsubscribed'),
        ('verify', 'Verified'),
        ('updated', 'Updated'),
    )
    
    subscription = models.ForeignKey(EmailSubscription, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscription.email} - {self.get_action_display()}"



class NotificationSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_messages = models.BooleanField(default=True)
    email_events = models.BooleanField(default=True)
    email_payments = models.BooleanField(default=True)
    app_messages = models.BooleanField(default=True)
    app_events = models.BooleanField(default=True)
    app_payments = models.BooleanField(default=True)
    quiet_start = models.TimeField(null=True, blank=True)
    quiet_end = models.TimeField(null=True, blank=True)
    digest = models.CharField(max_length=20, choices=[('never','Never'),('daily','Daily'),('weekly','Weekly')], default='never')




class Category(models.Model):
    """Category for blog posts and other content"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class BlogPost(models.Model):
    """Blog post model"""
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    content = RichTextField()
    excerpt = models.TextField(blank=True, help_text="Short summary of the post")
    
    # Author
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    
    # Media
    featured_image = models.ImageField(upload_to='blog/', null=True, blank=True)
    attachment = models.FileField(upload_to='blog/attachments/', null=True, blank=True)
    
    # Categorization
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='blog_posts')
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=True)
    
    # Statistics
    views = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
            # Ensure unique slug
            original_slug = self.slug
            counter = 1
            while BlogPost.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
    
    def get_tags_list(self):
        """Return tags as list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []


class BlogComment(models.Model):
    """Comments on blog posts"""
    blog = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_comments')
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.user.get_full_name()} on {self.blog.title}"


# ===== LIKE MODELS =====

class BlogPostLike(models.Model):
    """Likes on blog posts"""
    blog = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_post_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['blog', 'user']  # Prevent duplicate likes
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} liked {self.blog.title}"


class BlogCommentLike(models.Model):
    """Likes on blog comments"""
    comment = models.ForeignKey(BlogComment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['comment', 'user']  # Prevent duplicate likes
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} liked a comment on {self.comment.blog.title}"

class VideoVlog(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    youtube_url = models.URLField()
    thumbnail = models.ImageField(upload_to='vlogs/', null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vlogs')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    views = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title

class VideoVlogComment(models.Model):
    videovlog = models.ForeignKey('VideoVlog', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.content[:30]}"

class VideoVlogReport(models.Model):
    videovlog = models.ForeignKey(VideoVlog, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    reason = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


class StudentExecutive(models.Model):
    POSITIONS = (
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('secretary', 'Secretary'),
        ('treasurer', 'Treasurer'),
        ('organizer', 'Organizer'),
        ('welfare', 'Welfare Officer'),
        ('sports', 'Sports Director'),
        ('public_relations', 'Public Relations Officer'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='core_executive_profile')
    position = models.CharField(max_length=20, choices=POSITIONS)
    executive_year = models.CharField(max_length=9, help_text="e.g., 2023/2024")
    is_active = models.BooleanField(default=True)
    appointed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='appointed_executives')
    appointed_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_position_display()}"

class StudentDocument(models.Model):
    DOCUMENT_TYPES = (
        ('assignment', 'Assignment'),
        ('medical', 'Medical Report'),
        ('form', 'Form'),
        ('other', 'Other'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='student_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.title}"





# apps/core/models.py



class About(models.Model):
    """About page content model"""
    title = models.CharField(max_length=200, default="About MELTSA-TaTU")
    subtitle = models.CharField(max_length=300, blank=True, help_text="Short tagline or subtitle")
    
    # Main content sections
    mission = RichTextField(help_text="Mission statement")
    vision = RichTextField(help_text="Vision statement")
    history = RichTextField(help_text="Association history")
    
    # Statistics
    established_year = models.IntegerField(default=2010)
    total_members = models.IntegerField(default=0)
    total_executives = models.IntegerField(default=0)
    total_events = models.IntegerField(default=0)
    
    # Media
    featured_image = models.ImageField(upload_to='about/', blank=True, null=True, help_text="Main about page image")
    mission_image = models.ImageField(upload_to='about/', blank=True, null=True, help_text="Image for mission section")
    
    # Core values
    core_values = models.JSONField(default=list, blank=True, help_text="List of core values")
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True, max_length=500)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='about_updates')
    
    class Meta:
        verbose_name = "About Page"
        verbose_name_plural = "About Pages"
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Ensure only one about page exists
        if not self.pk and About.objects.exists():
            # If creating new and one exists, update existing instead
            existing = About.objects.first()
            for field in self._meta.fields:
                if field.name not in ['id', 'created_at']:
                    setattr(existing, field.name, getattr(self, field.name))
            existing.save(update_fields=[f.name for f in self._meta.fields if f.name not in ['id', 'created_at']])
            return existing
        return super().save(*args, **kwargs)


# apps/core/models.py

class ExecutiveTeam(models.Model):
    """Executive team members for about page"""
    POSITION_CHOICES = (
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('secretary', 'Secretary'),
        ('treasurer', 'Treasurer'),
        ('organizer', 'Organizer'),
        ('financial_sec', 'Financial Secretary'),
        ('welfare', 'Welfare Director'),
        ('sports', 'Sports Director'),
        ('academic', 'Academic Director'),
        ('public_relations', 'Public Relations Officer'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)
    custom_position = models.CharField(max_length=100, blank=True, help_text="If position is 'Other', specify here")
    
    bio = models.TextField(blank=True, help_text="Short biography")
    
    image = models.ImageField(upload_to='executive_team/', blank=True, null=True)
    
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Individual social media URL fields (better than JSONField)
    facebook_url = models.URLField(blank=True, verbose_name="Facebook Profile URL")
    twitter_url = models.URLField(blank=True, verbose_name="Twitter/X Profile URL")
    instagram_url = models.URLField(blank=True, verbose_name="Instagram Profile URL")
    linkedin_url = models.URLField(blank=True, verbose_name="LinkedIn Profile URL")
    whatsapp_url = models.URLField(blank=True, verbose_name="WhatsApp Link")
    website_url = models.URLField(blank=True, verbose_name="Personal Website")
    
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)
    
    joined_date = models.DateField(default=timezone.now)
    
    class Meta:
        ordering = ['order', 'position']
        verbose_name = "Executive Team Member"
        verbose_name_plural = "Executive Team"
    
    def __str__(self):
        return f"{self.name} - {self.get_position_display()}"
    
    @property
    def position_display(self):
        if self.position == 'other' and self.custom_position:
            return self.custom_position
        return self.get_position_display()
    
    @property
    def has_social_links(self):
        """Check if member has any social links"""
        return any([
            self.facebook_url,
            self.twitter_url,
            self.instagram_url,
            self.linkedin_url,
            self.whatsapp_url,
            self.website_url
        ])
 
class ContactInfo(models.Model):
    """Contact information for contact page"""
    # Primary contact
    primary_email = models.EmailField(help_text="Main contact email")
    primary_phone = models.CharField(max_length=20, help_text="Main contact phone")
    
    # Additional contacts
    support_email = models.EmailField(blank=True, help_text="Support email")
    support_phone = models.CharField(max_length=20, blank=True, help_text="Support phone")
    
    # Physical address
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100, default="Northern Region")
    country = models.CharField(max_length=100, default="Ghana")
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Map coordinates
    latitude = models.FloatField(default=9.4075, help_text="Google Maps latitude")
    longitude = models.FloatField(default=-0.8533, help_text="Google Maps longitude")
    
    # Social media
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=20, blank=True, help_text="WhatsApp number")
    
    # Office hours
    office_hours = models.TextField(blank=True, help_text="Office hours description")
    
    # Additional info
    additional_info = RichTextField(blank=True, help_text="Additional contact information")
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Contact Information"
        verbose_name_plural = "Contact Information"
    
    def __str__(self):
        return "Contact Information"
    
    def save(self, *args, **kwargs):
        # Ensure only one contact info exists
        if not self.pk and ContactInfo.objects.exists():
            existing = ContactInfo.objects.first()
            for field in self._meta.fields:
                if field.name not in ['id']:
                    setattr(existing, field.name, getattr(self, field.name))
            existing.save(update_fields=[f.name for f in self._meta.fields if f.name != 'id'])
            return existing
        return super().save(*args, **kwargs)


class ContactMessage(models.Model):
    """Contact form submissions"""
    STATUS_CHOICES = (
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('archived', 'Archived'),
    )
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    replied_at = models.DateTimeField(blank=True, null=True)
    replied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='replied_messages')
    reply_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
    
    def __str__(self):
        return f"{self.name} - {self.subject[:50]}"
    
    @property
    def is_new(self):
        return self.status == 'new'


class FAQ(models.Model):
    """Frequently Asked Questions"""
    CATEGORY_CHOICES = (
        ('general', 'General'),
        ('academic', 'Academic'),
        ('membership', 'Membership'),
        ('events', 'Events'),
        ('payments', 'Payments'),
        ('other', 'Other'),
    )
    
    question = models.CharField(max_length=300)
    answer = RichTextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'order', 'question']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        return self.question


class Partner(models.Model):
    """Partner organizations"""
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='partners/', blank=True, null=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
  

class Testimonial(models.Model):
    """Student testimonials for about page"""
    student_name = models.CharField(max_length=100)
    student_image = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    student_level = models.CharField(max_length=20, blank=True, help_text="e.g., Level 300")
    
    content = models.TextField()
    rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return f"{self.student_name} - {self.rating} stars"

class PrivacyPolicy(models.Model):
    """Privacy policy and terms of service"""
    title = models.CharField(max_length=200, default="Privacy Policy")
    content = models.TextField()
    
    # Version control
    version = models.CharField(max_length=20, help_text="e.g., v1.0, 2024-01")
    effective_date = models.DateField()
    is_current = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_privacy_policies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policies"
    
    def __str__(self):
        return f"{self.title} - {self.version}"
    
    def save(self, *args, **kwargs):
        if self.is_current:
            PrivacyPolicy.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)




class TermsOfService(models.Model):
    """Terms of service"""
    title = models.CharField(max_length=200, default="Terms of Service")
    content = models.TextField()
    
    # Version control
    version = models.CharField(max_length=20, help_text="e.g., v1.0, 2024-01")
    effective_date = models.DateField()
    is_current = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = "Terms of Service"
        verbose_name_plural = "Terms of Service"
    
    def __str__(self):
        return f"{self.title} - {self.version}"
    
    def save(self, *args, **kwargs):
        if self.is_current:
            TermsOfService.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)


