#include <linux/cdev.h>
#include <linux/device.h>
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/uaccess.h>

#define MODULE_NAME "mypipe"
#define BUFFER_SIZE 4096

MODULE_LICENSE("Dual MIT/GPL");
MODULE_AUTHOR("RainEggplant");
MODULE_DESCRIPTION("A simple pipe module for OS homework");

static char *mypipe_devnode(struct device *dev, umode_t *mode);
static ssize_t mypipe_write(struct file *filp, const char __user *buf,
                            size_t count, loff_t *ppos);
static ssize_t mypipe_read(struct file *filp, char __user *buf, size_t count,
                           loff_t *ppos);

static dev_t dev_no[2];
static char *dev_names[2] = {MODULE_NAME "_in", MODULE_NAME "_out"};
static struct cdev cdevs[2];
static struct class *mypipe_class;
static struct file_operations mypipe_fops[2] = {
    {.owner = THIS_MODULE, .write = mypipe_write},
    {.owner = THIS_MODULE, .read = mypipe_read}};
static char k_buf[BUFFER_SIZE];
static char *k_start, *k_end;
static struct mutex m_access, m_empty, m_full;

static int __init mypipe_init(void) {
  int ret = 0;
  struct device *dev;
  int i;

  printk(KERN_WARNING "mypipe init\n");

  // Allocate device number dynamicly. This can be viewed by running:
  //   cat /proc/devices
  ret = alloc_chrdev_region(dev_no, 0, 2, MODULE_NAME);
  if (ret < 0) {
    printk(KERN_ERR "failed to allocate device number!\n");
    goto alloc_err;
  }
  dev_no[1] = dev_no[0] + 1;
  printk(KERN_INFO "allocated major device number: %d\n", MAJOR(dev_no[0]));

  // Create device class
  mypipe_class = class_create(THIS_MODULE, MODULE_NAME);
  if (IS_ERR(mypipe_class)) {
    ret = PTR_ERR(mypipe_class);
    printk(KERN_ERR "class_create() failed\n");
    goto other_err;
  }
  mypipe_class->devnode = mypipe_devnode;

  for (i = 0; i < 2; ++i) {
    // Associate cdev with fop.
    cdev_init(&cdevs[i], &mypipe_fops[i]);
    // Add device to cdev_map table.
    ret = cdev_add(&cdevs[i], dev_no[i], 1);
    if (ret < 0) {
      printk(KERN_ERR "fail to add cdev\n");
      goto other_err;
    }
    // Create device node.
    dev = device_create(mypipe_class, NULL, dev_no[i], NULL, dev_names[i]);
    if (IS_ERR(dev)) {
      ret = PTR_ERR(dev);
      printk(KERN_ERR "device_create() failed\n");
      goto other_err;
    }
  }

  // Initialize mutexes and pointers.
  mutex_init(&m_access);
  mutex_init(&m_empty);
  mutex_init(&m_full);
  mutex_lock_killable(&m_empty);
  k_start = k_buf;
  k_end = k_buf;
  return 0;

other_err:
  // Unregister device number.
  unregister_chrdev_region(dev_no[0], 2);
alloc_err:
  return ret;
}

static void __exit mypipe_exit(void) {
  int i;
  for (i = 0; i < 2; ++i) {
    device_destroy(mypipe_class, dev_no[i]);
    cdev_del(&cdevs[i]);
  }

  class_destroy(mypipe_class);
  unregister_chrdev_region(dev_no[0], 2);
  mutex_destroy(&m_access);
  mutex_destroy(&m_empty);
  mutex_destroy(&m_full);

  printk(KERN_WARNING "mypipe exit\n");
}

static char *mypipe_devnode(struct device *dev, umode_t *mode) {
  if (mode != NULL) *mode = 0666;
  return NULL;
}

static ssize_t mypipe_write(struct file *filp, const char __user *buf,
                            size_t count, loff_t *ppos) {
  size_t blank_front, blank_rear, blank_size;
  size_t write_size;

  if (count == 0) return 0;

  // acquire mutex m_full and m_access, support restartable system call.
  if (mutex_lock_interruptible(&m_full)) return -ERESTARTSYS;
  if (mutex_lock_interruptible(&m_access)) {
    mutex_unlock(&m_full);
    return -ERESTARTSYS;
  }

  // when executed here, k_buf is always empty if k_start == k_end
  // because of mutex m_full.
  if (k_start <= k_end) {
    // .....s#####e.....
    blank_rear = k_buf + BUFFER_SIZE - k_end;
    blank_front = k_start - k_buf;
    blank_size = blank_rear + blank_front;
    if (count <= blank_rear) {
      // only fill the rear end.
      if (copy_from_user(k_end, buf, count)) goto err_copy;
      write_size = count;
      mutex_unlock(&m_full);
    } else if (count < blank_size) {
      // fill the rear end and the front end.
      if (copy_from_user(k_end, buf, blank_rear)) goto err_copy;
      if (copy_from_user(k_buf, buf + blank_rear, count - blank_rear))
        goto err_copy;
      write_size = count;
      mutex_unlock(&m_full);
    } else {
      // fill all empty space.
      if (copy_from_user(k_end, buf, blank_rear)) goto err_copy;
      if (copy_from_user(k_buf, buf + blank_rear, blank_front)) goto err_copy;
      write_size = blank_size;
    }
  } else {
    // #####e.....s#####
    blank_size = k_start - k_end;
    if (count < blank_size) {
      if (copy_from_user(k_end, buf, count)) goto err_copy;
      write_size = count;
      mutex_unlock(&m_full);
    } else {
      if (copy_from_user(k_end, buf, blank_size)) goto err_copy;
      write_size = blank_size;
    }
  }

  k_end = k_buf + (k_end - k_buf + write_size) % BUFFER_SIZE;
  // printk(KERN_INFO "Write %zu to k_buf", write_size);
  mutex_unlock(&m_empty);
  mutex_unlock(&m_access);
  return write_size;

err_copy:
  printk(KERN_ERR "Error copy_from_user()");
  mutex_unlock(&m_full);
  mutex_unlock(&m_access);
  return -EINVAL;
}

static ssize_t mypipe_read(struct file *filp, char __user *buf, size_t count,
                           loff_t *ppos) {
  size_t data_front, data_rear, data_size;
  size_t read_size;

  if (count == 0) return 0;

  // acquire mutex m_empty and m_access, support restartable system call.
  if (mutex_lock_interruptible(&m_empty)) return -ERESTARTSYS;
  if (mutex_lock_interruptible(&m_access)) {
    mutex_unlock(&m_empty);
    return -ERESTARTSYS;
  }

  // when executed here, k_buf is always full if k_start == k_end
  // because of mutex m_empty.
  if (k_start < k_end) {
    // .....s#####e.....
    data_size = k_end - k_start;
    if (count < data_size) {
      if (copy_to_user(buf, k_start, count)) goto err_copy;
      read_size = count;
      mutex_unlock(&m_empty);
    } else {
      if (copy_to_user(buf, k_start, data_size)) goto err_copy;
      read_size = data_size;
    }
  } else {
    // #####e.....s#####
    data_rear = k_buf + BUFFER_SIZE - k_start;
    data_front = k_end - k_buf;
    data_size = data_rear + data_front;
    if (count <= data_rear) {
      // only read the rear end.
      if (copy_to_user(buf, k_start, count)) goto err_copy;
      read_size = count;
      mutex_unlock(&m_empty);
    } else if (count < data_size) {
      // read the rear end and the front end.
      if (copy_to_user(buf, k_start, data_rear)) goto err_copy;
      if (copy_to_user(buf + data_rear, k_buf, count - data_rear))
        goto err_copy;
      read_size = count;
      mutex_unlock(&m_empty);
    } else {
      // read all data.
      if (copy_to_user(buf, k_start, data_rear)) goto err_copy;
      if (copy_to_user(buf + data_rear, k_buf, data_front)) goto err_copy;
      read_size = data_size;
    }
  }

  k_start = k_buf + (k_start - k_buf + read_size) % BUFFER_SIZE;
  // printk(KERN_INFO "Read %zu from k_buf", read_size);
  mutex_unlock(&m_full);
  mutex_unlock(&m_access);
  return read_size;

err_copy:
  printk(KERN_ERR "Error copy_to_user()");
  mutex_unlock(&m_empty);
  mutex_unlock(&m_access);
  return -EINVAL;
}

module_init(mypipe_init);
module_exit(mypipe_exit);
